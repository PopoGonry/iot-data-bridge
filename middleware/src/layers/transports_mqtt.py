"""
Transports Layer - MQTT Only
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
                    qos=device_config.get('qos', 1)
                )
                
            
            self.logger.info("디바이스로 메시지 전송",
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
    """Transports Layer - MQTT Only"""
    
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
            self.logger.info("Starting MQTT transports layer")
            
            if not self.config.mqtt:
                raise ValueError("MQTT configuration is required")
            
            self.transport = MQTTTransport(self.config.mqtt)
            self.is_running = True
            
            self.logger.info("MQTT transports layer started successfully")
            
        except Exception as e:
            self.logger.error("Failed to start MQTT transports layer", error=str(e))
            raise
    
    async def stop(self):
        """Stop transports layer"""
        self.logger.info("Stopping MQTT transports layer")
        self.is_running = False
        self.logger.info("MQTT transports layer stopped")
    
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
                # Create transport config (simplified - no device profile needed)
                transport_config = TransportConfig(
                    type=TransportType.MQTT,
                    config={
                        'topic': f'devices/{device_id.lower()}/ingress',
                        'qos': 1
                    }
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
                    # No console log - only file log
                    
                    success = await self.transport.send_to_device(device_target)
                    if success:
                        success_count += 1
                        # No console log - only file log
                        
                        # Log device ingest
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
                        
                except Exception as e:
                    self.logger.error("TRANSPORTS LAYER: Error delivering to device",
                                    trace_id=event.trace_id,
                                    device_id=device_target.device_id,
                                    error=str(e))
            
            # No console log - only file log
            
        except Exception as e:
            self._increment_error()
            self.logger.error("Error in send_to_devices",
                            trace_id=event.trace_id,
                            error=str(e))