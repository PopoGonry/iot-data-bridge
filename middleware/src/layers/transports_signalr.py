"""
Transports Layer - SignalR
Sends resolved events to target devices via SignalR (persistent connection, non-blocking, with reconnection)
"""

import asyncio
import json
import uuid
import contextlib
from datetime import datetime
from typing import Optional, Callable, List, Any, Awaitable
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

from layers.base import TransportsLayerInterface
from models.events import (
    ResolvedEvent,
    TransportEvent,
    DeviceTarget,
    TransportConfig,
    TransportType,
    DeviceIngestLog,
    LayerResult,
)
from models.config import TransportsConfig
from catalogs.device_catalog import DeviceCatalog


class SignalRTransport:
    """SignalR transport handler (persistent connection with auto-reconnect)."""

    def __init__(self, config):
        self.config = config
        self.logger = structlog.get_logger("signalr_transport")
        self.connection: Optional[BaseHubConnection] = None
        self._is_open: bool = False
        self._reconnector_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()  # serialize .send() if needed

    async def start(self):
        """Initialize and open a persistent SignalR connection."""
        if not SIGNALR_AVAILABLE:
            raise ImportError("SignalR library not available")
        await self._open_connection()

    async def stop(self):
        """Stop reconnect loop and close the connection."""
        if self._reconnector_task:
            self._reconnector_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._reconnector_task
            self._reconnector_task = None
        await self.close_connection()

    async def _open_connection(self):
        """Create and start a SignalR connection (non-blocking stabilization)."""
        # Clean any previous connection just in case
        await self.close_connection()

        self.connection = HubConnectionBuilder().with_url(self.config.url).build()

        # Wire events
        self.connection.on_open(self._on_open)
        self.connection.on_close(self._on_close)
        self.connection.on_error(lambda e: self.logger.error("signalr error", error=str(e)))

        # Small async delay to ensure hub object readiness (non-blocking)
        await asyncio.sleep(0.05)

        # Start (sync; library spins its own thread)
        self.connection.start()

        # Small stabilization window (non-blocking)
        await asyncio.sleep(0.2)

    def _on_open(self):
        self._is_open = True
        self.logger.info("signalr transport opened")

    def _on_close(self):
        self._is_open = False
        self.logger.warning("signalr transport closed; scheduling reconnect")

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # Shutting down or no loop available
            return

        if self._reconnector_task is None or self._reconnector_task.done():
            self._reconnector_task = loop.create_task(self._reconnect_loop())

    async def _reconnect_loop(self):
        """Try reconnecting with exponential backoff until open or stop() is called."""
        delay = 1
        while not self._is_open:
            try:
                await asyncio.sleep(delay)
                await self.close_connection()
                await self._open_connection()
                if self._is_open:
                    self.logger.info("signalr transport reconnected")
                    return
            except Exception as e:
                self.logger.error("reconnect failed", error=str(e))
                delay = min(delay * 2, 30)

    async def _ensure_connected(self):
        """Ensure an open connection before sending."""
        if self.connection is None or not self._is_open:
            await self._open_connection()

    async def send_to_device(self, device_target: DeviceTarget) -> bool:
        """
        Send data to target device via SignalR.
        Uses persistent connection; ensures connection and sends.
        """
        await self._ensure_connected()

        async with self._lock:
            try:
                # Device-specific config
                cfg = device_target.transport_config.config or {}
                group = cfg.get("group", device_target.device_id)
                target = cfg.get("target", "ingress")

                # Prepare payload with absolute time + trace_id
                payload = {
                    "trace_id": str(uuid.uuid4()),
                    "object": device_target.object,
                    "value": device_target.value,
                    "timestamp": datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
                }

                # Send to hub method (server must implement this signature)
                self.connection.send("SendMessage", [group, target, json.dumps(payload)])
                self.logger.debug("signalr send ok", group=group, target=target, device=device_target.device_id)
                return True

            except Exception as e:
                self.logger.error("send failed", device_id=device_target.device_id, error=str(e))
                # Optionally trigger reconnect on failure
                self._on_close()
                return False

    async def close_connection(self):
        """Close the SignalR connection, ignoring shutdown errors."""
        if self.connection:
            with contextlib.suppress(Exception):
                self.connection.stop()
            self.connection = None
            self._is_open = False
            self.logger.info("signalr transport connection closed")


class TransportsLayer(TransportsLayerInterface):
    """Transports Layer - SignalR only."""

    def __init__(
        self,
        config: TransportsConfig,
        device_catalog: DeviceCatalog,
        device_ingest_callback: Callable[[DeviceIngestLog], Awaitable[None]],
    ):
        super().__init__("transports_layer")
        self.config = config
        self.device_catalog = device_catalog
        self.device_ingest_callback = device_ingest_callback
        self.transport: Optional[SignalRTransport] = None
        self.is_running = False

        if not self.config.signalr:
            raise ValueError("SignalR configuration is required")
        self.transport = SignalRTransport(self.config.signalr)

    async def start(self) -> None:
        """Start transports layer and open persistent SignalR connection."""
        if not SIGNALR_AVAILABLE:
            raise ImportError("SignalR library not available")
        self.is_running = True
        await self.transport.start()

    async def stop(self) -> None:
        """Stop transports layer and close SignalR connection."""
        self.is_running = False
        if self.transport:
            await self.transport.stop()

    async def send_to_devices(self, event: ResolvedEvent) -> LayerResult:
        """
        Send a resolved event to all target devices via SignalR.
        Sequential by default; can be adapted to bounded concurrency if needed.
        """
        self._increment_processed()

        # Build device targets
        device_targets: List[DeviceTarget] = [
            DeviceTarget(
                device_id=device_id,
                transport_config=TransportConfig(
                    type=TransportType.SIGNALR,
                    config={"group": device_id, "target": "ingress"},
                ),
                object=event.object,
                value=event.value,
            )
            for device_id in event.target_devices
        ]

        success_count = 0

        # Option: simple sequential sends (predictable backpressure).
        for dt in device_targets:
            ok = await self.transport.send_to_device(dt)
            if ok:
                success_count += 1
                # Device ingest log callback (async)
                await self.device_ingest_callback(
                    DeviceIngestLog(
                        trace_id=event.trace_id,
                        device_id=dt.device_id,
                        object=dt.object,
                        value=dt.value,
                    )
                )
            else:
                self.logger.warning(
                    "transport: failed to deliver to device",
                    trace_id=event.trace_id,
                    device_id=dt.device_id,
                )

        # If you need bounded concurrency, replace above loop with:
        # sem = asyncio.Semaphore(16)
        # async def _send(dt):
        #     async with sem:
        #         return await self.transport.send_to_device(dt)
        # results = await asyncio.gather(*[_send(dt) for dt in device_targets], return_exceptions=True)
        # success_count = sum(bool(r) and not isinstance(r, Exception) for r in results)

        return LayerResult(
            success=success_count > 0,
            processed_count=len(device_targets),
            error_count=len(device_targets) - success_count,
            data=device_targets,
        )
