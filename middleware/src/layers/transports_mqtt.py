"""
Transports Layer - MQTT Sends resolved events to target devices
"""

import asyncio
import json
from typing import Optional, Callable, List
import structlog

from aiomqtt import Client as MQTTClient

from layers.base import TransportsLayerInterface
from models.events import ResolvedEvent, TransportEvent, DeviceTarget, TransportConfig, TransportType, DeviceIngestLog
from models.config import TransportsConfig
from catalogs.device_catalog import DeviceCatalog


class MQTTTransport:
    """MQTT transport handler"""
    
    def __init__(self, config):
        self.config = config
        self.logger = structlog.get_logger("mqtt_transport")
        self.client = None
    
    async def send_to_device(self, device_target: DeviceTarget) -> bool:
        """Send data to device via MQTT"""
        try:
            if not self.client:
                self.client = MQTTClient(
                    hostname=self.config.host,
                    port=self.config.port,
                    username=self.config.username,
                    password=self.config.password,
                    keepalive=self.config.keepalive
                )
            
            # Get device-specific topic
            device_config = device_target.transport_config.config
            topic = device_config.get('topic', f"devices/{device_target.device_id}/ingress")
            
            # Prepare payload
            payload = {
                "object": device_target.object,
                "value": device_target.value
            }
            
            # Send message
            async with self.client:
                await self.client.publish(
                    topic,
                    payload=json.dumps(payload),
                    qos=self.config.qos
                )
            
            self.logger.debug("Sent MQTT message to device",
                            device_id=device_target.device_id,
                            topic=topic,
                            object=device_target.object,
                            value=device_target.value)
            
            return True
            
        except Exception as e:
            self.logger.error("Error sending MQTT message",
                            device_id=device_target.device_id,
                            error=str(e))
            return False


class TransportsLayer(TransportsLayerInterface):
    """Transports Layer - MQTT only"""
    
    def __init__(self, config: TransportsConfig, device_catalog: DeviceCatalog):
        super().__init__(config, device_catalog)
        self.transport_handler = None
        
        # Initialize transport handler based on transport type
        if self.config.type == "mqtt":
            if not self.config.mqtt:
                raise ValueError("MQTT configuration is required for MQTT transport type")
            self.transport_handler = MQTTTransport(self.config.mqtt)
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
