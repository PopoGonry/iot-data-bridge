"""
Transports Layer - SignalR: Sends resolved events to target devices (stabilized)
- structlog 로깅 일원화
- 연결 수명 분리: start()/stop()
- on_close 안전 재연결(쓰레드→메인루프 위임)
- 전송 실패시 자동 재시도(1회)
- 워치독(유휴/half-open 감지 후 안전 재시작)
- 동시성 가드: 초기화/전송 락
- UTC ISO 타임스탬프 사용
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Optional, Callable, List, Any
import contextlib
import inspect
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
    TransportConfig,
    TransportType,
    DeviceTarget,
    DeviceIngestLog,
    LayerResult,
)
from models.config import TransportsConfig
from catalogs.device_catalog import DeviceCatalog


class SignalRTransport:
    """
    SignalR transport handler (single connection reused)
    - Use start()/stop() to manage connection lifecycle
    - Thread-safe reconnection scheduling
    """

    def __init__(self, config):
        self.config = config
        self.logger = structlog.get_logger("signalr_transport")
        self.connection: Optional[BaseHubConnection] = None
        self.main_loop: Optional[asyncio.AbstractEventLoop] = None
        self.is_running: bool = False

        # 동시성/수명 관리
        self._init_lock = asyncio.Lock()     # 연결 생성/재시작 가드
        self._send_lock = asyncio.Lock()     # 전송 시퀀싱 가드
        self._reconnect_lock = asyncio.Lock()
        self._reconnect_task: Optional[asyncio.Task] = None

        # 워치독
        self._watchdog_task: Optional[asyncio.Task] = None
        self.idle_timeout_sec: int = getattr(self.config, "idle_timeout_sec", 90)
        self._last_activity_ts: float = 0.0

        # 허브 메서드 이름/옵션
        # 서버 허브 구현에 맞게 필요시 이 이름을 맞추세요. 기본은 "SendMessage"
        self._hub_method_send: str = getattr(self.config, "method_send", "SendMessage")
        # 선택: 서버가 핑을 받을 수 있다면 설정 (없으면 워치독은 재시작만 수행)
        self._hub_method_ping: Optional[str] = getattr(self.config, "method_ping", None)

    # ---------- Public lifecycle ----------

    async def start(self):
        """Create and start the SignalR connection (awaitable; raises on failure)."""
        if not SIGNALR_AVAILABLE:
            self.logger.error("SignalR library not available. Install signalrcore.")
            raise ImportError("SignalR library not available")

        self.main_loop = asyncio.get_running_loop()
        async with self._init_lock:
            await self._teardown_connection(silent=True)
            self._build_connection()
            await asyncio.sleep(0.05)
            self.connection.start()
            await asyncio.sleep(0.15)

            self.is_running = True
            self._touch_activity()
            self.logger.info("SignalR transport started")

            self._start_watchdog()

    async def stop(self):
        """Stop transport and cleanup connection."""
        self.is_running = False
        await self._stop_watchdog()
        await self._cancel_reconnect_task()
        async with self._init_lock:
            await self._teardown_connection(silent=False)
        self.logger.info("SignalR transport stopped")

    # ---------- Sending ----------

    async def send_to_device(self, device_target: DeviceTarget) -> bool:
        """
        Send data to device via SignalR.
        - Safe for concurrent calls; internally serialized by _send_lock.
        - On failure, tries one reconnect+retry.
        """
        payload = self._build_payload(device_target)
        group = device_target.transport_config.config.get("group", device_target.device_id)
        target = device_target.transport_config.config.get("target", "ingress")

        # 1st attempt
        ok = await self._try_send_once(group, target, payload)
        if ok:
            self._touch_activity()
            return True

        # Reconnect & retry once
        self.logger.warning("Send failed; attempting reconnect and retry",
                            device_id=device_target.device_id)
        await self._restart_connection()
        ok2 = await self._try_send_once(group, target, payload)
        if ok2:
            self._touch_activity()
        return ok2

    # ---------- Internals ----------

    def _build_connection(self):
        """Build hub connection and wire handlers."""
        self.logger.debug("Building SignalR transport connection", url=self.config.url)
        self.connection = HubConnectionBuilder().with_url(self.config.url).build()

        # on_open
        def _on_open():
            self.logger.info("SignalR transport connection opened")

        # on_close (external thread) → schedule reconnection on main loop
        def _on_close(*args, **kwargs):
            self.logger.warning("SignalR transport connection closed; scheduling reconnection",
                                args=args, kwargs=kwargs)
            if self.main_loop and self.main_loop.is_running():
                asyncio.run_coroutine_threadsafe(self._attempt_reconnection(), self.main_loop)
            else:
                self.logger.warning("Main loop not available; reconnection skipped")

        self.connection.on_open(_on_open)
        self.connection.on_close(_on_close)
        self.connection.on_error(lambda data: self.logger.error("SignalR transport connection error", data=data))

    async def _teardown_connection(self, silent: bool):
        """Stop and drop current connection."""
        if not self.connection:
            return
        try:
            try:
                self.connection.stop()
            except Exception as e:
                if not silent:
                    self.logger.debug("Connection stop error (ignored)", error=str(e))
        finally:
            self.connection = None

    async def _try_send_once(self, group: str, target: str, payload: dict) -> bool:
        """Single attempt to send; returns True/False."""
        async with self._send_lock:
            try:
                if not self.connection:
                    # Lazy-start safeguard if connection was dropped
                    await self._restart_connection()
                # SignalR hub method: [group, target, json_payload]
                self.connection.send(self._hub_method_send, [group, target, json.dumps(payload)])
                return True
            except Exception as e:
                self.logger.error("SignalR send error", group=group, target=target, error=str(e))
                return False

    def _touch_activity(self):
        loop = asyncio.get_running_loop()
        self._last_activity_ts = loop.time()

    def _build_payload(self, device_target: DeviceTarget) -> dict:
        # UTC ISO timestamp for cross-system consistency
        ts = datetime.now(timezone.utc).isoformat()
        return {
            "object": device_target.object,
            "value": device_target.value,
            "timestamp": ts,
            "device_id": device_target.device_id,
        }

    # ---------- Reconnection ----------

    async def _attempt_reconnection(self):
        """Ensure a single reconnect loop is running."""
        async with self._reconnect_lock:
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
        delay = 1
        while self.is_running:
            try:
                await asyncio.sleep(delay)
                self.logger.info("SignalR transport reconnect attempt", delay=delay)
                await self._restart_connection()
                self.logger.info("SignalR transport reconnected")
                return
            except Exception as e:
                self.logger.error("SignalR transport reconnect failed", error=str(e))
                delay = min(delay * 2, 30)

    async def _restart_connection(self):
        """Tear down and re-create connection under init lock."""
        async with self._init_lock:
            if not self.is_running:
                return
            await self._teardown_connection(silent=True)
            self._build_connection()
            await asyncio.sleep(0.05)
            self.connection.start()
            await asyncio.sleep(0.15)
            self._touch_activity()
            self.logger.info("SignalR transport connection restarted")

    # ---------- Watchdog ----------

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
        """Idle/half-open watchdog. If idle too long, either ping or restart."""
        try:
            while self.is_running:
                await asyncio.sleep(10)
                if not self.is_running:
                    break
                loop = asyncio.get_running_loop()
                idle = loop.time() - self._last_activity_ts if self._last_activity_ts else 0
                if self.idle_timeout_sec and idle > self.idle_timeout_sec:
                    self.logger.warning("Transport idle timeout; recovering", idle_sec=int(idle))
                    # Try ping if configured; else restart
                    if self._hub_method_ping and self.connection:
                        try:
                            # fire-and-forget ping (no await API on signalrcore send)
                            self.connection.send(self._hub_method_ping, [])
                            self._touch_activity()
                            continue
                        except Exception as e:
                            self.logger.warning("Ping failed; restarting transport", error=str(e))
                    await self._restart_connection()
        except asyncio.CancelledError:
            pass


class TransportsLayer(TransportsLayerInterface):
    """Transports Layer - SignalR only"""

    def __init__(
        self,
        config: TransportsConfig,
        device_catalog: DeviceCatalog,
        device_ingest_callback: Callable[[DeviceIngestLog], Any],
    ):
        super().__init__("transports_layer")
        self.logger = structlog.get_logger("transports_layer")
        self.config = config
        self.device_catalog = device_catalog
        self.device_ingest_callback = device_ingest_callback
        self.transport: Optional[SignalRTransport] = None
        self.is_running = False

        if not self.config.signalr:
            raise ValueError("SignalR configuration is required")
        self.transport = SignalRTransport(self.config.signalr)

        # 콜백 async/sync 지원 플래그
        self._callback_is_async = inspect.iscoroutinefunction(self.device_ingest_callback)

    async def start(self) -> None:
        await self.transport.start()
        self.is_running = True

    async def stop(self) -> None:
        self.is_running = False
        if self.transport:
            await self.transport.stop()

    async def send_to_devices(self, event: ResolvedEvent) -> LayerResult:
        """
        - event.target_devices: List[str] (device_id들)
        - 각 device_id를 group으로 사용하고 target은 기본 'ingress'
          (필요 시 TransportConfig 구성으로 오버라이드)
        """
        self._increment_processed()

        device_targets: List[DeviceTarget] = []
        for device_id in event.target_devices:
            transport_config = TransportConfig(
                type=TransportType.SIGNALR,
                config={"group": device_id, "target": "ingress"},
            )
            device_targets.append(
                DeviceTarget(
                    device_id=device_id,
                    transport_config=transport_config,
                    object=event.object,
                    value=event.value,
                )
            )

        success_count = 0
        error_count = 0

        # 순차 전송(허브가 메시지 순서 보장되길 원할 때 안전)
        # 필요 시 gather로 병렬화 가능하나, 허브/서버 특성 고려하세요.
        for dt in device_targets:
            try:
                ok = await self.transport.send_to_device(dt)
                if ok:
                    success_count += 1
                    # ingest 로그 콜백 (sync/async 자동 처리)
                    ingest_log = DeviceIngestLog(
                        trace_id=event.trace_id,
                        device_id=dt.device_id,
                        object=dt.object,
                        value=dt.value,
                    )
                    if self._callback_is_async:
                        await self.device_ingest_callback(ingest_log)
                    else:
                        # sync 함수는 스레드풀로 넘겨 event loop 블로킹 방지
                        loop = asyncio.get_running_loop()
                        await loop.run_in_executor(None, self.device_ingest_callback, ingest_log)
                else:
                    error_count += 1
                    self.logger.warn(
                        "TRANSPORTS: Failed to deliver to device",
                        trace_id=event.trace_id,
                        device_id=dt.device_id,
                    )
            except Exception as e:
                error_count += 1
                self.logger.error(
                    "TRANSPORTS: Error delivering to device",
                    trace_id=event.trace_id,
                    device_id=dt.device_id,
                    error=str(e),
                )

        return LayerResult(
            success=success_count > 0 and error_count == 0,
            processed_count=len(device_targets),
            error_count=error_count,
            data=device_targets,
        )
