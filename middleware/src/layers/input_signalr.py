#!/usr/bin/env python3
"""
IoT Data Bridge - SignalR Input Layer (stabilized)
- structlog 로깅 일원화
- on_close 안전 재연결 (쓰레드→메인루프 스케줄)
- JoinGroup 백오프 재시도
- 워치독(무수신 idle 감지) + 안전 재시작
- 재연결 락/가드(중복 방지)
- start/stop 수명주기 정리
"""

import asyncio
import json
import uuid
import time
from typing import Optional, Callable, Any, Awaitable
import contextlib
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

from layers.base import InputLayerInterface  # 상위 입력 레이어 공통 인터페이스
from models.events import IngressEvent       # IngressEvent(trace_id, raw, meta)
from models.config import InputConfig        # InputConfig.signalr: { url, group, ... }


class SignalRInputHandler:
    """SignalR input handler"""

    def __init__(self, config, callback: Callable[[IngressEvent], Awaitable[None]]):
        self.config = config
        self.callback = callback
        self.logger = structlog.get_logger("signalr_input")
        self.connection: Optional[BaseHubConnection] = None
        self.is_running = False
        self.main_loop: Optional[asyncio.AbstractEventLoop] = None
        self.last_message_time = 0.0

        # 재연결/워치독 관리
        self._reconnect_lock = asyncio.Lock()
        self._reconnect_task: Optional[asyncio.Task] = None
        self._watchdog_task: Optional[asyncio.Task] = None
        self.idle_timeout_sec = 60  # 무수신 60초면 재시작

    async def start(self):
        """Start SignalR connection (awaitable, 예외 상위 전파)"""
        self.logger.debug("SignalRInputHandler.start called", url=self.config.url, group=self.config.group)

        if not SIGNALR_AVAILABLE:
            self.logger.error("SignalR library not available. Install signalrcore.")
            raise ImportError("SignalR library not available")

        # 메인 이벤트 루프 레퍼런스 저장
        self.main_loop = asyncio.get_running_loop()
        self.logger.debug("Stored main loop reference", loop_is_running=self.main_loop.is_running())

        # 기존 연결이 남아있다면 정리
        await self._teardown_connection(silent=True)

        try:
            # 연결 생성/핸들러 바인딩
            self._build_connection()

            # 아주 짧은 대기(허브 준비)
            await asyncio.sleep(0.1)

            # 연결 시작 (signalrcore 내부 쓰레드 가동)
            self.connection.start()

            # 약간의 안정화 대기
            await asyncio.sleep(0.2)

            self.is_running = True
            self.last_message_time = time.time()
            self.logger.info("SignalRInputHandler started", group=self.config.group)

            # 워치독 시작
            self._start_watchdog()

        except Exception as e:
            import traceback
            self.logger.error("SignalR start failed", error=str(e), traceback=traceback.format_exc())
            raise

    async def stop(self):
        """Stop SignalR connection"""
        self.logger.debug("SignalRInputHandler.stop called", is_running=self.is_running)
        self.is_running = False

        # 워치독 중지
        await self._stop_watchdog()

        # 재연결 태스크 중지
        await self._cancel_reconnect_task()

        # 연결 정리
        await self._teardown_connection(silent=False)

        self.logger.info("SignalR connection stopped")

    # -------------------------
    # 내부 유틸
    # -------------------------
    def _build_connection(self):
        """Hub 연결 객체 생성 및 이벤트 핸들러 등록"""
        self.logger.debug("Building SignalR connection", url=self.config.url)
        self.connection = HubConnectionBuilder().with_url(self.config.url).build()

        # 메시지 핸들러 - 서버에서 보내는 이벤트 이름과 맞춤
        self.connection.on("ingress", self._on_message)

        # 연결 오픈 시: 그룹 조인(백오프 재시도)
        def _on_open():
            self.logger.info("SignalR connection opened")
            async def _join_with_backoff():
                backoff = 0.2
                for _ in range(5):
                    try:
                        self.connection.send("JoinGroup", [self.config.group])
                        self.logger.info("Joined SignalR group", group=self.config.group)
                        return
                    except Exception as e:
                        self.logger.warning("JoinGroup failed; retrying", error=str(e), backoff=backoff)
                        await asyncio.sleep(backoff)
                        backoff = min(backoff * 2, 2.0)
                self.logger.error("JoinGroup failed permanently", group=self.config.group)

            if self.main_loop and self.main_loop.is_running():
                asyncio.run_coroutine_threadsafe(_join_with_backoff(), self.main_loop)
            else:
                self.logger.warning("Main loop not available on open; skipping JoinGroup")

        # 연결 종료 시: 안전 재연결 스케줄
        def _on_close(*args, **kwargs):
            self._on_connection_close(*args, **kwargs)

        self.connection.on_open(_on_open)
        self.connection.on_close(_on_close)
        self.connection.on_error(lambda data: self.logger.error("SignalR connection error", data=data))

    async def _teardown_connection(self, silent: bool):
        """연결 종료 및 정리"""
        if not self.connection:
            return
        try:
            try:
                # 그룹 이탈은 best-effort
                self.connection.send("LeaveGroup", [self.config.group])
            except Exception as e:
                if not silent:
                    self.logger.debug("LeaveGroup error (ignored)", error=str(e))
            try:
                self.connection.stop()
            except Exception as e:
                if not silent:
                    self.logger.debug("Connection stop error (ignored)", error=str(e))
        finally:
            self.connection = None

    def _start_watchdog(self):
        if self._watchdog_task and not self._watchdog_task.done():
            return
        self._watchdog_task = asyncio.create_task(self._watchdog())

    async def _stop_watchdog(self):
        if self._watchdog_task:
            self._watchdog_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._watchdog_task
            self._watchdog_task = None

    async def _watchdog(self):
        """무수신 idle 감지 → 안전 재시작"""
        try:
            while self.is_running:
                await asyncio.sleep(10)
                if not self.is_running:
                    break
                if self.last_message_time and (time.time() - self.last_message_time > self.idle_timeout_sec):
                    self.logger.warning("Idle timeout detected; restarting connection",
                                        idle_sec=time.time() - self.last_message_time)
                    await self._restart_connection()
        except asyncio.CancelledError:
            pass

    async def _restart_connection(self):
        """연결 재시작 (락/가드 하에서 호출 권장)"""
        # 외부 호출도 고려하여 락으로 감쌈
        async with self._reconnect_lock:
            if not self.is_running:
                return
            self.logger.info("Restarting SignalR connection")
            await self._teardown_connection(silent=True)
            # 재빌드 + 재시작
            self._build_connection()
            await asyncio.sleep(0.1)
            self.connection.start()
            await asyncio.sleep(0.2)
            self.last_message_time = time.time()
            self.logger.info("SignalR connection restarted")

    async def _attempt_reconnection(self):
        """재연결 루프 태스크를 스케줄(중복 방지)"""
        async with self._reconnect_lock:
            # 이미 재연결 태스크가 돌고 있으면 무시
            if self._reconnect_task and not self._reconnect_task.done():
                return
            self._reconnect_task = asyncio.create_task(self._reconnect_loop())

    async def _cancel_reconnect_task(self):
        if self._reconnect_task:
            self._reconnect_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._reconnect_task
            self._reconnect_task = None

    async def _reconnect_loop(self):
        """지수 백오프 재연결 루프"""
        delay = 1
        while self.is_running:
            try:
                await asyncio.sleep(delay)
                self.logger.info("Reconnect attempt", delay=delay)
                # 완전 재시작 경로 사용
                await self._restart_connection()
                self.logger.info("SignalR input reconnected")
                return
            except Exception as e:
                self.logger.error("Reconnect failed", error=str(e))
                delay = min(delay * 2, 30)

    # -------------------------
    # SignalR 이벤트 콜백
    # -------------------------
    def _on_message(self, *args):
        """Handle incoming SignalR message (signalrcore 내부 쓰레드에서 호출됨)"""
        self.last_message_time = time.time()
        message = None
        try:
            self.logger.debug("SignalR message received", args_count=len(args), args=args)
            if not args:
                self.logger.warning("Empty SignalR message")
                return

            first = args[0]
            self.logger.debug("Processing message", first_arg=first, first_type=type(first))
            
            # SignalR 메시지 형태 처리: {"type":1,"target":"ingress","arguments":[...]}
            if isinstance(first, dict) and "arguments" in first:
                # SignalR 표준 메시지 형태
                arguments = first.get("arguments", [])
                if arguments and len(arguments) > 0:
                    payload = arguments[0]  # 첫 번째 argument를 payload로 사용
                    message = str(first)
                else:
                    self.logger.warning("Empty arguments in SignalR message")
                    return
            elif isinstance(first, str):
                # JSON 문자열 형태
                payload = json.loads(first)
                message = first
            elif isinstance(first, list) and first and isinstance(first[0], str):
                # 리스트의 첫 번째 요소가 JSON 문자열
                payload = json.loads(first[0])
                message = first[0]
            else:
                # 기타 형태
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

            # 항상 메인 루프로 안전하게 위임
            if self.main_loop and self.main_loop.is_running():
                fut = asyncio.run_coroutine_threadsafe(self.callback(ingress_event), self.main_loop)

                def _done(f):
                    try:
                        f.result()
                    except Exception as e:
                        self.logger.error("Mapping callback failed", error=str(e), trace_id=trace_id)
                fut.add_done_callback(_done)
            else:
                # 종료/정리 중이면 드랍
                self.logger.warning("Main loop unavailable; dropping message", trace_id=trace_id)

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

    def _on_connection_close(self, *args, **kwargs):
        """Handle connection close - schedule reconnection on main loop"""
        self.logger.warning("SignalR input connection closed; scheduling reconnection...", args=args, kwargs=kwargs)
        if self.main_loop and self.main_loop.is_running():
            # 외부 쓰레드에서 호출되므로 run_coroutine_threadsafe 사용
            asyncio.run_coroutine_threadsafe(self._attempt_reconnection(), self.main_loop)
        else:
            # 종료 중이라면 무시
            self.logger.warning("Main loop not available; reconnection skipped (probably shutting down)")

# ----------------------------------------
# InputLayer 구현
# ----------------------------------------
class InputLayer(InputLayerInterface):
    """Input Layer - SignalR only"""

    def __init__(self, config: InputConfig, mapping_layer_callback: Callable[[IngressEvent], Awaitable[None]]):
        super().__init__("input_layer")
        self.config = config
        self.mapping_layer_callback = mapping_layer_callback
        self.handler: Optional[SignalRInputHandler] = None

        if not self.config.signalr:
            raise ValueError("SignalR configuration is required")
        self.handler = SignalRInputHandler(self.config.signalr, self._on_ingress_event)

    async def start(self):
        # 예외 전파(초기화 실패를 상위에서 감지 가능)
        await self.handler.start()
        self.is_running = True

    async def stop(self):
        self.is_running = False
        if self.handler:
            await self.handler.stop()

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
