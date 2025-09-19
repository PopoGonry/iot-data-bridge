"""
Transports Layer - MQTT Sends resolved events to target devices
"""

import asyncio
import json
import uuid
from typing import Optional, Callable, List, Any
import structlog

from aiomqtt import Client as MQTTClient

from layers.base import TransportsLayerInterface
from models.events import ResolvedEvent, TransportEvent, DeviceTarget, TransportConfig, TransportType, DeviceIngestLog, LayerResult
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
        super().__init__("mqtt_transports")
        self.config = config
        self.device_catalog = device_catalog
        self.transport_handler = None
        
        # Initialize transport handler based on transport type
        if self.config.type == "mqtt":
            if not self.config.mqtt:
                raise ValueError("MQTT configuration is required for MQTT transport type")
            self.transport_handler = MQTTTransport(self.config.mqtt)
        else:
            raise ValueError(f"Unsupported transport type: {self.config.type}")
    
    async def start(self) -> None:
        """Start transports layer"""
        self.is_running = True
        self.logger.info("Transports layer started")
    
    async def stop(self) -> None:
        """Stop transports layer"""
        self.is_running = False
        self.logger.info("Transports layer stopped")
    
    async def send_to_devices(self, event: Any) -> LayerResult:
        """Send event to target devices"""
        try:
            if not isinstance(event, ResolvedEvent):
                raise ValueError(f"Expected ResolvedEvent, got {type(event)}")
            
            transport_events = await self.send_event(event)
            
            successful_count = sum(1 for e in transport_events if e.success)
            total_count = len(transport_events)
            
            return LayerResult(
                success=successful_count > 0,
                processed_count=total_count,
                error_count=total_count - successful_count,
                data=transport_events
            )
            
        except Exception as e:
            self.logger.error("Error in send_to_devices", error=str(e))
            self._increment_error()
            return LayerResult(
                success=False,
                processed_count=0,
                error_count=1,
                data=None
            )
    
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
