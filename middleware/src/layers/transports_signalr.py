"""
Transports Layer - SignalR Sends resolved events to target devices
"""

import asyncio
import json
import uuid
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
    """SignalR transport handler with connection pooling and batch processing"""
    
    def __init__(self, config):
        self.config = config
        self.logger = structlog.get_logger("signalr_transport")
        self.connection: Optional[BaseHubConnection] = None
        self._connection_lock = asyncio.Lock()
        self._is_connected = False
    
    async def _ensure_connection(self):
        """Ensure SignalR connection is established"""
        if self._is_connected and self.connection:
            return
        
        async with self._connection_lock:
            if self._is_connected and self.connection:
                return
                
            try:
                self.connection = HubConnectionBuilder() \
                    .with_url(self.config.url) \
                    .build()
                
                # Add event handlers
                self.connection.on_open(lambda: self.logger.debug("SignalR transport connection opened"))
                self.connection.on_close(lambda: self.logger.debug("SignalR transport connection closed"))
                self.connection.on_error(lambda data: self.logger.error("SignalR transport connection error", error=data))
                
                self.connection.start()
                
                # Wait for connection to stabilize asynchronously
                await asyncio.sleep(1)
                
                self._is_connected = True
                self.logger.info("SignalR transport connection established")
                
            except Exception as e:
                self.logger.error("Failed to establish SignalR connection", error=str(e))
                self._is_connected = False
                raise
    
    async def send_to_device(self, device_target: DeviceTarget) -> bool:
        """Send data to device via SignalR"""
        try:
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
            
            # Send message to device group
            self.connection.send("SendMessage", [group, target, json.dumps(payload)])
            
            return True
            
        except Exception as e:
            self.logger.error("Error sending SignalR message",
                            device_id=device_target.device_id,
                            error=str(e))
            self._is_connected = False  # Mark connection as failed
            return False
    
    async def send_batch_to_devices(self, device_targets: List[DeviceTarget]) -> List[bool]:
        """Send batch data to multiple devices via SignalR"""
        try:
            await self._ensure_connection()
            
            # Group targets by group name for batch processing
            groups = {}
            for target in device_targets:
                device_config = target.transport_config.config
                group = device_config.get('group', target.device_id)
                target_name = device_config.get('target', 'ingress')
                
                if group not in groups:
                    groups[group] = []
                
                payload = {
                    "object": target.object,
                    "value": target.value,
                    "timestamp": asyncio.get_event_loop().time()
                }
                
                groups[group].append({
                    "target": target_name,
                    "payload": payload,
                    "device_id": target.device_id
                })
            
            # Send batch messages to each group
            results = []
            for group, messages in groups.items():
                try:
                    # Use batch message sending if available
                    batch_payload = json.dumps([msg["payload"] for msg in messages])
                    self.connection.send("SendBatchMessages", [group, messages[0]["target"], batch_payload])
                    results.extend([True] * len(messages))
                except Exception as e:
                    self.logger.error("Error sending batch message to group", group=group, error=str(e))
                    results.extend([False] * len(messages))
            
            return results
            
        except Exception as e:
            self.logger.error("Error sending batch SignalR messages", error=str(e))
            self._is_connected = False
            return [False] * len(device_targets)


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
    
    async def stop(self) -> None:
        self.is_running = False
    
    async def send_to_devices(self, event: ResolvedEvent) -> LayerResult:
        self._increment_processed()
        device_targets = []
        for device_id in event.target_devices:
            transport_config = TransportConfig(
                type=TransportType.SIGNALR,
                config={'group': device_id, 'target': 'ingress'}
            )
            device_target = DeviceTarget(device_id=device_id, transport_config=transport_config, object=event.object, value=event.value)
            device_targets.append(device_target)
        
        # Use batch processing for better performance
        if len(device_targets) > 1:
            # Try batch processing first
            try:
                batch_results = await self.transport.send_batch_to_devices(device_targets)
                success_count = sum(1 for result in batch_results if result)
                
                # Log successful device ingests
                for i, (device_target, success) in enumerate(zip(device_targets, batch_results)):
                    if success:
                        ingest_log = DeviceIngestLog(
                            trace_id=event.trace_id,
                            device_id=device_target.device_id,
                            object=device_target.object,
                            value=device_target.value
                        )
                        await self.device_ingest_callback(ingest_log)
                    else:
                        self.logger.warning("TRANSPORTS LAYER: Failed to deliver to device", 
                                          trace_id=event.trace_id,
                                          device_id=device_target.device_id)
                
                return LayerResult(success=success_count > 0, processed_count=len(device_targets), error_count=len(device_targets) - success_count, data=device_targets)
                
            except Exception as e:
                self.logger.warning("Batch processing failed, falling back to individual sends", error=str(e))
        
        # Fallback to individual processing with parallel execution
        async def send_single_device(device_target):
            try:
                success = await self.transport.send_to_device(device_target)
                if success:
                    # Log device ingest
                    ingest_log = DeviceIngestLog(
                        trace_id=event.trace_id,
                        device_id=device_target.device_id,
                        object=device_target.object,
                        value=device_target.value
                    )
                    await self.device_ingest_callback(ingest_log)
                    return True
                else:
                    self.logger.warning("TRANSPORTS LAYER: Failed to deliver to device", 
                                      trace_id=event.trace_id,
                                      device_id=device_target.device_id)
                    return False
                    
            except Exception as e:
                self.logger.error("TRANSPORTS LAYER: Error delivering to device",
                                trace_id=event.trace_id,
                                device_id=device_target.device_id,
                                error=str(e))
                return False
        
        # Execute all device sends in parallel
        results = await asyncio.gather(*[send_single_device(target) for target in device_targets], return_exceptions=True)
        
        # Count successes and handle exceptions
        success_count = 0
        for result in results:
            if isinstance(result, bool) and result:
                success_count += 1
            elif isinstance(result, Exception):
                self.logger.error("Exception in parallel device send", error=str(result))
        
        return LayerResult(success=success_count > 0, processed_count=len(device_targets), error_count=len(device_targets) - success_count, data=device_targets)