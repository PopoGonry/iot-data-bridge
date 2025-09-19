"""
Transports Layer - SignalR Sends resolved events to target devices
"""

import asyncio
import json
import uuid
from typing import Optional, Callable, List
import structlog

try:
    from signalrcore import HubConnection
    SIGNALR_AVAILABLE = True
except ImportError:
    SIGNALR_AVAILABLE = False
    HubConnection = None

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
                self.connection = HubConnection(self.config.url)
                
                if self.config.username and self.config.password:
                    # Note: Authentication may need to be handled differently
                    # depending on the signalrcore version
                    pass
                await self.connection.start()
            
            # Get device-specific configuration
            device_config = device_target.transport_config.config
            group = device_config.get('group', device_target.device_id)
            
            # Prepare payload
            payload = {
                "object": device_target.object,
                "value": device_target.value,
                "timestamp": asyncio.get_event_loop().time()
            }
            
            # Send message to device group
            await self.connection.invoke("SendToGroup", group, json.dumps(payload))
            
            self.logger.debug("Sent SignalR message to device",
                            device_id=device_target.device_id,
                            group=group,
                            object=device_target.object,
                            value=device_target.value)
            
            return True
            
        except Exception as e:
            self.logger.error("Error sending SignalR message",
                            device_id=device_target.device_id,
                            error=str(e))
            return False


class TransportsLayer(TransportsLayerInterface):
    """Transports Layer - SignalR only"""
    
    def __init__(self, config: TransportsConfig, device_catalog: DeviceCatalog):
        super().__init__(config, device_catalog)
        self.transport_handler = None
        
        # Initialize transport handler based on transport type
        if self.config.type == "signalr":
            if not self.config.signalr:
                raise ValueError("SignalR configuration is required for SignalR transport type")
            self.transport_handler = SignalRTransport(self.config.signalr)
        else:
            raise ValueError(f"Unsupported transport type: {self.config.type}")
    
    async def send_event(self, resolved_event: ResolvedEvent) -> List[TransportEvent]:
        """Send resolved event to target devices"""
        transport_events = []
        
        try:
            # Get target devices for each object
            for object_name, value in resolved_event.mapped_data.items():
                target_devices = self.device_catalog.get_devices_for_object(object_name)
                
                for device_id in target_devices:
                    # Create device target
                    device_target = DeviceTarget(
                        device_id=device_id,
                        object=object_name,
                        value=value,
                        transport_config=self.device_catalog.get_device_transport_config(device_id)
                    )
                    
                    # Send to device
                    success = await self.transport_handler.send_to_device(device_target)
                    
                    # Create transport event
                    transport_event = TransportEvent(
                        uuid=str(uuid.uuid4()),
                        timestamp=asyncio.get_event_loop().time(),
                        resolved_event_uuid=resolved_event.uuid,
                        device_target=device_target,
                        success=success
                    )
                    
                    transport_events.append(transport_event)
                    
                    # Log device ingest
                    if success:
                        device_log = DeviceIngestLog(
                            device_id=device_id,
                            object=object_name,
                            value=value,
                            timestamp=asyncio.get_event_loop().time()
                        )
                        self.logger.info("Device data ingested", 
                                       device_id=device_id,
                                       object=object_name,
                                       value=value)
            
            self.logger.info("Transport events processed",
                           total_events=len(transport_events),
                           successful=sum(1 for e in transport_events if e.success))
            
        except Exception as e:
            self.logger.error("Error in transport layer", error=str(e))
        
        return transport_events
