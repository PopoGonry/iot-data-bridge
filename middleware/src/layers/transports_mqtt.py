#!/usr/bin/env python3
"""
IoT Data Bridge - SignalR Input Layer (merged & fixed)
"""

import asyncio
import json
import uuid
import time
from typing import Optional, Callable, Any, Awaitable
import structlog

try:
    from signalrcore.hub_connection_builder import HubConnectionBuilder
    from signalrcore.hub.base_hub_connection import BaseHubConnection
    SIGNALR_AVAILABLE = True
except ImportError as e:
    print(f"SignalR import error: {e}")
    SIGNALR_AVAILABLE = False
    HubConnectionBuilder = None
    BaseHubConnection = None

from layers.base import InputLayerInterface
    # InputLayerInterface: 상위 입력 레이어 공통 인터페이스
from models.events import IngressEvent
    # IngressEvent(trace_id, raw, meta)
from models.config import InputConfig
    # InputConfig.signalr: { url, group, ... }


class SignalRInputHandler:
    """SignalR input handler"""

    def __init__(self, config, callback: Callable[[IngressEvent], Awaitable[None]]):
        self.config = config
        self.callback = callback
        self.logger = structlog.get_logger("signalr_input")
        self.connection: Optional[BaseHubConnection] = None
        self.is_running = False
        self.main_loop: Optional[asyncio.AbstractEventLoop] = None
        self.last_message_time = 0

    async def start(self):
        """Start SignalR connection (non-blocking)"""
        self.logger.debug("SignalRInputHandler.start called", url=self.config.url, group=self.config.group)

        if not SIGNALR_AVAILABLE:
            self.logger.error("SignalR is not available. Please install signalrcore library.")
            raise ImportError("SignalR library not available")

        # Store reference to main event loop
        self.main_loop = asyncio.get_running_loop()
        self.logger.debug("Stored main loop reference", running=self.main_loop.is_running())

        try:
            # Build connection
            self.logger.debug("Building SignalR connection", url=self.config.url)
            self.connection = HubConnectionBuilder().with_url(self.config.url).build()

            # Register message handler for ingress messages
            self.connection.on("ingress", self._on_message)

            # Connection event handlers
            def _on_open():
                print("[DEBUG] SignalR connection opened successfully")
                # Join group right after connection opens
                try:
                    self.connection.send("JoinGroup", [self.config.group])
                    print(f"[DEBUG] Joined group: {self.config.group}")
                    self.logger.info("Joined SignalR group", group=self.config.group)
                except Exception as e:
                    print(f"[DEBUG] JoinGroup error: {e}")
                    self.logger.error("JoinGroup error", error=str(e))

            self.connection.on_open(_on_open)
            self.connection.on_close(self._on_connection_close)  # wire reconnection path
            self.connection.on_error(lambda data: print(f"[DEBUG] SignalR connection error: {data}"))

            # Brief async wait to ensure hub object is ready (non-blocking)
            await asyncio.sleep(0.1)

            # Start connection (sync call that spins an internal thread)
            self.connection.start()
            # Give a tiny stabilization window (non-blocking)
            await asyncio.sleep(0.2)

            self.is_running = True
            self.logger.info("SignalRInputHandler started", group=self.config.group)

        except Exception as e:
            import traceback
            self.logger.error("SignalR connection error", error=str(e), traceback=traceback.format_exc())
            raise

    async def stop(self):
        """Stop SignalR connection"""
        self.logger.debug("SignalRInputHandler.stop called", is_running=self.is_running)
        self.is_running = False

        if self.connection:
            try:
                # Best-effort LeaveGroup
                try:
                    self.connection.send("LeaveGroup", [self.config.group])
                except Exception:
                    pass

                # Stop connection
                try:
                    self.connection.stop()
                except Exception:
                    pass
            finally:
                self.connection = None

        self.logger.info("SignalR connection stopped")

    def _on_message(self, *args):
        """Handle incoming SignalR message (called from signalrcore thread)"""
        self.last_message_time = time.time()
        message = None
        try:
            if not args:
                self.logger.warning("Empty SignalR message")
                return

            first = args[0]
            # Normalize payload
            if isinstance(first, str):
                payload = json.loads(first)
                message = first
            elif isinstance(first, list) and first and isinstance(first[0], str):
                payload = json.loads(first[0])
                message = first[0]
            else:
                payload = first
                message = repr(first)

            trace_id = str(uuid.uuid4())
            ingress_event = IngressEvent(
                trace_id=trace_id,
                raw=payload,
                meta={
                    "source": "signalr",
                    "group": self.config.group,
                    "target": "ingress",
                },
            )

            # Schedule callback coroutine safely on main loop
            if self.main_loop and self.main_loop.is_running():
                fut = asyncio.run_coroutine_threadsafe(self.callback(ingress_event), self.main_loop)

                def _done(f):
                    try:
                        f.result()
                    except Exception as e:
                        self.logger.error("Mapping callback failed", error=str(e), trace_id=trace_id)
                fut.add_done_callback(_done)
            else:
                # Fallback: run synchronously with its own loop (last resort)
                asyncio.run(self.callback(ingress_event))

        except json.JSONDecodeError as e:
            self.logger.error("Invalid JSON in SignalR message", error=str(e), message=message)
        except Exception as e:
            import traceback
            self.logger.error(
                "Error processing SignalR message",
                error=str(e),
                message=message,
                traceback=traceback.format_exc(),
            )

    def _on_connection_close(self):
        """Handle connection close - attempt reconnection"""
        self.logger.warning("SignalR input connection closed, attempting reconnection...")
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._attempt_reconnection())
        except RuntimeError:
            # No running loop (e.g., shutting down) → ignore
            pass

    async def _attempt_reconnection(self):
        """Attempt to reconnect with exponential backoff while is_running"""
        delay = 1
        while self.is_running:
            try:
                await asyncio.sleep(delay)
                self.logger.info("Reconnect attempt", delay=delay)
                await self.start()
                self.logger.info("SignalR input reconnected")
                return
            except Exception as e:
                self.logger.error("Reconnect failed", error=str(e))
                delay = min(delay * 2, 30)  # cap at 30s


class InputLayer(InputLayerInterface):
    """Input Layer - SignalR only"""

    def __init__(self, config: InputConfig, mapping_layer_callback: Callable[[IngressEvent], Awaitable[None]]):
        super().__init__("input_layer")
        self.config = config
        self.mapping_layer_callback = mapping_layer_callback
        self.handler: Optional[SignalRInputHandler] = None
        self._task: Optional[asyncio.Task] = None  # initialize

        if not self.config.signalr:
            raise ValueError("SignalR configuration is required")
        self.handler = SignalRInputHandler(self.config.signalr, self._on_ingress_event)

    async def start(self):
        self._task = asyncio.create_task(self.handler.start())
        self.is_running = True

    async def stop(self):
        self.is_running = False
        if self.handler:
            await self.handler.stop()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            finally:
                self._task = None

    async def process_raw_data(self, raw_data: dict, meta: dict) -> Optional[Any]:
        """
        외부에서 수동 주입 시 사용 가능한 헬퍼.
        현재 설계는 IngressEvent만 생성해서 반환합니다.
        파이프라인으로 즉시 투입하려면 아래 주석을 해제하세요.
        """
        trace_id = str(uuid.uuid4())
        ingress_event = IngressEvent(trace_id=trace_id, raw=raw_data, meta=meta)
        # 즉시 처리하고 싶다면:
        # await self.mapping_layer_callback(ingress_event)
        return ingress_event

    async def _on_ingress_event(self, event: IngressEvent):
        self._increment_processed()
        await self.mapping_layer_callback(event)
