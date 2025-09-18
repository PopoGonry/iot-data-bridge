"""
Transports Layer - Sends resolved events to target devices
"""

import asyncio
import json
from typing import Optional, Callable, List
import structlog

from aiomqtt import Client as MQTTClient
from signalrcore import HubConnectionBuilder

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
                "value": device_target.value,
                "timestamp": asyncio.get_event_loop().time()
            }
            
            # Send message
            async with self.client:
                await self.client.publish(
                    topic,
                    payload=json.dumps(payload),
                    qos=device_config.get('qos', 1)
                )
            
            self.logger.debug("Sent MQTT message to device",
                            device_id=device_target.device_id,
                            topic=topic,
                            object=device_target.object)
            
            return True
            
        except Exception as e:
            self.logger.error("Error sending MQTT message",
                            device_id=device_target.device_id,
                            error=str(e))
            return False


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
            
            # Send message
            await self.connection.invoke("SendToGroup", group, target, payload)
            
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
    """Transports Layer - Sends ResolvedEvent to target devices"""
    
    def __init__(self, config: TransportsConfig, device_catalog: DeviceCatalog, logging_callback: Callable[[DeviceIngestLog], None]):
        super().__init__("transports_layer")
        self.config = config
        self.device_catalog = device_catalog
        self.logging_callback = logging_callback
        self.transport_handler = None
    
    async def start(self):
        """Start transports layer"""
        try:
            self.logger.info("Starting transports layer", type=self.config.type)
            
            if self.config.type == "mqtt":
                if not self.config.mqtt:
                    raise ValueError("MQTT configuration is required for MQTT transport type")
                self.transport_handler = MQTTTransport(self.config.mqtt)
                
            elif self.config.type == "signalr":
                if not self.config.signalr:
                    raise ValueError("SignalR configuration is required for SignalR transport type")
                self.transport_handler = SignalRTransport(self.config.signalr)
                
            else:
                raise ValueError(f"Unsupported transport type: {self.config.type}")
            
            self.is_running = True
            self.logger.info("Transports layer started successfully")
            
        except Exception as e:
            self.logger.error("Failed to start transports layer", error=str(e))
            raise
    
    async def stop(self):
        """Stop transports layer"""
        self.logger.info("Stopping transports layer")
        self.is_running = False
        self.logger.info("Transports layer stopped")
    
    async def send_to_devices(self, event: ResolvedEvent) -> bool:
        """Send resolved event to target devices"""
        try:
            self._increment_processed()
            
            self.logger.debug("Sending event to devices",
                            trace_id=event.trace_id,
                            object=event.object,
                            target_devices=event.target_devices)
            
            # Create device targets
            device_targets = []
            for device_id in event.target_devices:
                device_profile = self.device_catalog.get_device_profile(device_id)
                if not device_profile:
                    self.logger.warning("No profile found for device",
                                      device_id=device_id)
                    continue
                
                # Get transport configuration
                transport_config_data = device_profile.get_transport_config(self.config.type)
                if not transport_config_data:
                    self.logger.warning("No transport config found for device",
                                      device_id=device_id,
                                      transport_type=self.config.type)
                    continue
                
                # Create device target
                device_target = DeviceTarget(
                    device_id=device_id,
                    transport_config=TransportConfig(
                        type=TransportType(self.config.type),
                        config=transport_config_data
                    ),
                    object=event.object,
                    value=event.value
                )
                device_targets.append(device_target)
            
            if not device_targets:
                self.logger.warning("No valid device targets found",
                                  trace_id=event.trace_id)
                self._increment_error()
                return False
            
            # Send to each device
            success_count = 0
            for device_target in device_targets:
                try:
                    success = await self.transport_handler.send_to_device(device_target)
                    if success:
                        success_count += 1
                        
                        # Log device ingest
                        await self._log_device_ingest(device_target)
                        
                except Exception as e:
                    self.logger.error("Error sending to device",
                                    device_id=device_target.device_id,
                                    error=str(e))
            
            self.logger.info("Sent event to devices",
                           trace_id=event.trace_id,
                           total_devices=len(device_targets),
                           success_count=success_count)
            
            return success_count > 0
            
        except Exception as e:
            self._increment_error()
            self.logger.error("Error sending to devices", 
                            error=str(e), 
                            trace_id=event.trace_id)
            return False
    
    async def _log_device_ingest(self, device_target: DeviceTarget):
        """Log device ingest event"""
        try:
            device_ingest_log = DeviceIngestLog(
                device_id=device_target.device_id,
                object=device_target.object,
                value=device_target.value
            )
            
            await self.logging_callback(device_ingest_log)
            
        except Exception as e:
            self.logger.error("Error logging device ingest", 
                            error=str(e), 
                            device_id=device_target.device_id)
