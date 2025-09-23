"""
Transports Layer - SignalR Only
"""

import asyncio
import json
from typing import Optional, Callable, List
import structlog

from signalrcore import HubConnectionBuilder

from layers.base import TransportsLayerInterface
from models.events import ResolvedEvent, TransportEvent, DeviceTarget, TransportConfig, TransportType, DeviceIngestLog
from models.config import TransportsConfig
from catalogs.device_catalog import DeviceCatalog


class SignalRTransport:
    """SignalR transport handler"""
    
    def __init__(self, config):
        self.config = config
        self.logger = structlog.get_logger("signalr_transport")
        self.connection = None
    
    async def send_to_device(self, device_target: DeviceTarget) -> bool:
        """Send data to device via SignalR"""
        try:
            if not self.connection:
                builder = HubConnectionBuilder()
                builder.with_url(self.config.url)
                
                if self.config.username and self.config.password:
                    builder.with_authentication(self.config.username, self.config.password)
                
                self.connection = builder.build()
                await self.connection.start()
            
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
            
            # Send message to group
            await self.connection.invoke("SendToGroup", group, target, json.dumps(payload))
            
            self.logger.debug("Sent SignalR message to device",
                            device_id=device_target.device_id,
                            group=group,
                            target=target,
                            object=device_target.object)
            
            return True
            
        except Exception as e:
            self.logger.error("Error sending SignalR message",
                            device_id=device_target.device_id,
                            error=str(e))
            return False


class TransportsLayer(TransportsLayerInterface):
    """Transports Layer - SignalR Only"""
    
    def __init__(self, config: TransportsConfig, device_catalog: DeviceCatalog, device_ingest_callback: Callable[[DeviceIngestLog], None]):
        super().__init__("transports_layer")
        self.config = config
        self.device_catalog = device_catalog
        self.device_ingest_callback = device_ingest_callback
        self.transport = None
        self.is_running = False
    
    async def start(self):
        """Start transports layer"""
        try:
            self.logger.info("Starting SignalR transports layer")
            
            if not self.config.signalr:
                raise ValueError("SignalR configuration is required")
            
            self.transport = SignalRTransport(self.config.signalr)
            self.is_running = True
            
            self.logger.info("SignalR transports layer started successfully")
            
        except Exception as e:
            self.logger.error("Failed to start SignalR transports layer", error=str(e))
            raise
    
    async def stop(self):
        """Stop transports layer"""
        self.logger.info("Stopping SignalR transports layer")
        self.is_running = False
        self.logger.info("SignalR transports layer stopped")
    
    async def send_to_devices(self, event: ResolvedEvent):
        """Send resolved event to target devices"""
        try:
            self._increment_processed()
            
            self.logger.debug("Sending to devices",
                            trace_id=event.trace_id,
                            object=event.object,
                            target_devices=event.target_devices)
            
            # Create device targets
            device_targets = []
            for device_id in event.target_devices:
                device_profile = self.device_catalog.get_device_profile(device_id)
                if not device_profile:
                    self.logger.warning("Device profile not found", device_id=device_id)
                    continue
                
                # Create transport config
                transport_config = TransportConfig(
                    type=TransportType.SIGNALR,
                    config=device_profile.signalr_config
                )
                
                # Create device target
                device_target = DeviceTarget(
                    device_id=device_id,
                    transport_config=transport_config,
                    object=event.object,
                    value=event.value
                )
                
                device_targets.append(device_target)
            
            # Send to all devices
            success_count = 0
            for device_target in device_targets:
                try:
                    success = await self.transport.send_to_device(device_target)
                    if success:
                        success_count += 1
                        
                        # Log device ingest
                        ingest_log = DeviceIngestLog(
                            device_id=device_target.device_id,
                            object=device_target.object,
                            value=device_target.value
                        )
                        await self.device_ingest_callback(ingest_log)
                        
                except Exception as e:
                    self.logger.error("Error sending to device",
                                    device_id=device_target.device_id,
                                    error=str(e))
            
            self.logger.info("Sent to devices",
                           trace_id=event.trace_id,
                           total_devices=len(device_targets),
                           success_count=success_count)
            
        except Exception as e:
            self._increment_error()
            self.logger.error("Error in send_to_devices",
                            trace_id=event.trace_id,
                            error=str(e))
