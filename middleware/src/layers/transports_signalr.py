"""
Transports Layer - SignalR Sends resolved events to target devices
"""

import asyncio
import json
import uuid
import traceback
from datetime import datetime
from typing import Optional, Callable, List, Any
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
from models.events import ResolvedEvent, TransportEvent, DeviceTarget, TransportConfig, TransportType, DeviceIngestLog, LayerResult
from models.config import TransportsConfig
from catalogs.device_catalog import DeviceCatalog


class SignalRTransport:
    """SignalR transport handler"""
    
    def __init__(self, config):
        self.config = config
        self.logger = structlog.get_logger("signalr_transport")
        self.connection: Optional[BaseHubConnection] = None
        self.connection_retry_count = 0
        self.max_retries = 3
        self.retry_delay = 2
        self.is_running = False  # 실행 상태 추가
        self.send_queue = asyncio.Queue(maxsize=500)  # 전송 큐
        self.active_sends = set()  # 활성 전송 태스크 추적
    
    async def send_to_device(self, device_target: DeviceTarget) -> bool:
        """Send data to device via SignalR"""
        try:
            # 큐에 전송 요청 추가
            await self.send_queue.put(device_target)
            return True
            
        except Exception as e:
            self.logger.error("Error queuing SignalR message",
                            device_id=device_target.device_id,
                            error=str(e))
            return False
    
    async def _process_send_queue(self):
        """Process send queue with timeout and error handling"""
        while self.is_running:  # 중단 조건 추가
            try:
                # 큐에서 전송 요청 가져오기
                device_target = await asyncio.wait_for(self.send_queue.get(), timeout=1.0)
                await self._safe_send_message(device_target)
            except asyncio.TimeoutError:
                continue  # 타임아웃은 정상, 계속 대기
            except Exception as e:
                self.logger.error("Error in send queue processing", error=str(e))
                await asyncio.sleep(0.1)
    
    async def _safe_send_message(self, device_target: DeviceTarget) -> bool:
        """Safely send message with timeout and retry"""
        for attempt in range(3):  # 3번 재시도
            try:
                if not self.connection or not self._is_connection_active():
                    await self._ensure_connection()
                
                # Get device-specific configuration
                device_config = device_target.transport_config.config
                group = device_config.get('group', device_target.device_id)
                target = device_config.get('target', 'ingress')
                
                # Prepare payload
                payload = {
                    "object": device_target.object,
                    "value": device_target.value,
                    "timestamp": asyncio.get_event_loop().time()
                }
                
                # Send message with timeout
                send_task = asyncio.create_task(self._send_message_with_timeout(group, target, payload))
                self.active_sends.add(send_task)
                
                try:
                    await asyncio.wait_for(send_task, timeout=3.0)
                    self.active_sends.discard(send_task)
                    return True
                except asyncio.TimeoutError:
                    self.logger.warning("Send message timeout", 
                                      device_id=device_target.device_id, 
                                      attempt=attempt + 1)
                    send_task.cancel()
                    self.active_sends.discard(send_task)
                    if attempt < 2:
                        await asyncio.sleep(0.5)
                        continue
                    return False
                    
            except Exception as e:
                self.logger.error("Error sending SignalR message",
                                device_id=device_target.device_id,
                                attempt=attempt + 1,
                                error=str(e))
                if attempt < 2:
                    await asyncio.sleep(0.5)
                    continue
                return False
        
        return False
    
    async def _send_message_with_timeout(self, group: str, target: str, payload: dict):
        """Send message with timeout wrapper"""
        # SignalR send는 동기 함수이므로 별도 스레드에서 실행
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.connection.send, "SendMessage", [group, target, json.dumps(payload)])
    
    def _is_connection_active(self) -> bool:
        """Check if SignalR connection is active"""
        if not self.connection:
            return False
        
        try:
            if hasattr(self.connection, 'transport') and hasattr(self.connection.transport, '_ws'):
                return self.connection.transport._ws and self.connection.transport._ws.sock
        except Exception:
            pass
        
        return False
    
    async def _ensure_connection(self):
        """Ensure SignalR connection is established"""
        if self.connection and self._is_connection_active():
            return
        
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                if self.connection:
                    try:
                        self.connection.stop()
                    except Exception:
                        pass
                
                self.connection = HubConnectionBuilder() \
                    .with_url(self.config.url) \
                    .build()
                
                # Add event handlers
                self.connection.on_open(self._on_connection_open)
                self.connection.on_close(self._on_connection_close)
                self.connection.on_error(self._on_connection_error)
                
                self.connection.start()
                
                # Wait for connection to stabilize
                await asyncio.sleep(1)
                
                if self._is_connection_active():
                    self.connection_retry_count = 0
                    self.logger.info("SignalR transport connection established")
                    return
                else:
                    raise ConnectionError("Connection not active after start")
                    
            except Exception as e:
                retry_count += 1
                self.logger.warning(f"Failed to establish SignalR transport connection (attempt {retry_count}/{self.max_retries}): {e}")
                
                if retry_count < self.max_retries:
                    await asyncio.sleep(self.retry_delay)
                else:
                    self.logger.error("Max retries exceeded for SignalR transport connection")
                    raise
    
    def _on_connection_open(self):
        """Handle connection open event"""
        self.logger.debug("SignalR transport connection opened")
        self.connection_retry_count = 0
    
    def _on_connection_close(self):
        """Handle connection close event"""
        self.logger.warning("SignalR transport connection closed")
    
    def _on_connection_error(self, data):
        """Handle connection error event"""
        self.logger.error("SignalR transport connection error", error=data)


class TransportsLayer(TransportsLayerInterface):
    """Transports Layer - SignalR only"""
    
    def __init__(self, config: TransportsConfig, device_catalog: DeviceCatalog, device_ingest_callback: Callable[[DeviceIngestLog], None]):
        super().__init__("transports_layer")
        self.config = config
        self.device_catalog = device_catalog
        self.device_ingest_callback = device_ingest_callback
        self.transport = None
        self.is_running = False
        
        if not self.config.signalr:
            raise ValueError("SignalR configuration is required")
        self.transport = SignalRTransport(self.config.signalr)
    
    async def start(self) -> None:
        self.is_running = True
        self.transport.is_running = True  # Transport도 실행 상태로 설정
        # Ensure transport connection is established first
        await self.transport._ensure_connection()
        # Start send queue processing task
        asyncio.create_task(self.transport._process_send_queue())
    
    async def stop(self) -> None:
        self.is_running = False
        self.transport.is_running = False  # Transport도 중지 상태로 설정
        # 모든 활성 전송 태스크 정리
        for task in self.transport.active_sends:
            task.cancel()
        if self.transport.active_sends:
            await asyncio.gather(*self.transport.active_sends, return_exceptions=True)
    
    async def send_to_devices(self, event: ResolvedEvent) -> LayerResult:
        try:
            self._increment_processed()
            device_targets = []
            for device_id in event.target_devices:
                transport_config = TransportConfig(
                    type=TransportType.SIGNALR,
                    config={'group': device_id, 'target': 'ingress'}
                )
                device_target = DeviceTarget(device_id=device_id, transport_config=transport_config, object=event.object, value=event.value)
                device_targets.append(device_target)
            
            success_count = 0
            for device_target in device_targets:
                try:
                    # 큐에 추가하고 즉시 성공으로 처리 (비동기 처리)
                    success = await self.transport.send_to_device(device_target)
                    if success:
                        success_count += 1
                        
                        # Log device ingest (비동기)
                        ingest_log = DeviceIngestLog(
                            trace_id=event.trace_id,
                            device_id=device_target.device_id,
                            object=device_target.object,
                            value=device_target.value
                        )
                        asyncio.create_task(self.device_ingest_callback(ingest_log))
                    else:
                        self.logger.warning("TRANSPORTS LAYER: Failed to queue device delivery", 
                                          trace_id=event.trace_id,
                                          device_id=device_target.device_id)
                        
                except Exception as e:
                    self.logger.error("TRANSPORTS LAYER: Error queuing device delivery",
                                    trace_id=event.trace_id,
                                    device_id=device_target.device_id,
                                    error=str(e))
            
            return LayerResult(success=success_count > 0, processed_count=len(device_targets), error_count=len(device_targets) - success_count, data=device_targets)
        except Exception as e:
            self.logger.error("TRANSPORTS LAYER: Critical error in send_to_devices", 
                            trace_id=event.trace_id,
                            error=str(e),
                            traceback=traceback.format_exc())
            return LayerResult(
                success=False,
                processed_count=0,
                error_count=len(event.target_devices) if hasattr(event, 'target_devices') else 1,
                data=[]
            )