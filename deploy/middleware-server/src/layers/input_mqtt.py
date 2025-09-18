"""
Input Layer - MQTT Only
"""

import asyncio
import json
import uuid
from typing import Optional, Callable, Any
import structlog

from aiomqtt import Client as MQTTClient

from layers.base import InputLayerInterface
from models.events import IngressEvent
from models.config import InputConfig


class MQTTInputHandler:
    """MQTT input handler"""
    
    def __init__(self, config, callback: Callable[[IngressEvent], None]):
        self.config = config
        self.callback = callback
        self.logger = structlog.get_logger("mqtt_input")
        self.client = None
        self.is_running = False
    
    async def start(self):
        """Start MQTT client"""
        try:
            self.client = MQTTClient(
                hostname=self.config.host,
                port=self.config.port,
                username=self.config.username,
                password=self.config.password,
                keepalive=self.config.keepalive
            )
            
            async with self.client:
                self.is_running = True
                self.logger.info("MQTT client started", 
                               host=self.config.host, 
                               port=self.config.port,
                               topic=self.config.topic)
                
                async for message in self.client.messages:
                    if not self.is_running:
                        break
                    
                    try:
                        await self._process_message(message)
                    except Exception as e:
                        self.logger.error("Error processing message", error=str(e))
                        
        except Exception as e:
            self.logger.error("MQTT client error", error=str(e))
            raise
    
    async def stop(self):
        """Stop MQTT client"""
        self.logger.info("Stopping MQTT client")
        self.is_running = False
        if self.client:
            await self.client.disconnect()
    
    async def _process_message(self, message):
        """Process incoming MQTT message"""
        try:
            # Parse message payload
            payload = json.loads(message.payload.decode('utf-8'))
            
            # Generate trace ID
            trace_id = str(uuid.uuid4())
            
            # Create ingress event
            ingress_event = IngressEvent(
                trace_id=trace_id,
                raw=payload,
                meta={
                    "source": "mqtt",
                    "topic": message.topic,
                    "qos": message.qos
                }
            )
            
            # Send to mapping layer
            await self.callback(ingress_event)
            
            self.logger.debug("Processed MQTT message", 
                            trace_id=trace_id,
                            topic=message.topic)
            
        except json.JSONDecodeError as e:
            self.logger.error("Invalid JSON in MQTT message", error=str(e))
        except Exception as e:
            self.logger.error("Error processing MQTT message", error=str(e))


class InputLayer(InputLayerInterface):
    """Input Layer - MQTT Only"""
    
    def __init__(self, config: InputConfig, mapping_layer_callback: Callable[[IngressEvent], None]):
        super().__init__("input_layer")
        self.config = config
        self.mapping_layer_callback = mapping_layer_callback
        self.handler = None
        self._task = None
    
    async def start(self):
        """Start input layer"""
        try:
            self.logger.info("Starting MQTT input layer")
            
            if not self.config.mqtt:
                raise ValueError("MQTT configuration is required")
            
            self.handler = MQTTInputHandler(
                self.config.mqtt,
                self._on_ingress_event
            )
            
            # Start handler in background task
            self._task = asyncio.create_task(self.handler.start())
            self.is_running = True
            
            self.logger.info("MQTT input layer started successfully")
            
        except Exception as e:
            self.logger.error("Failed to start MQTT input layer", error=str(e))
            raise
    
    async def stop(self):
        """Stop input layer"""
        self.logger.info("Stopping MQTT input layer")
        self.is_running = False
        
        if self.handler:
            await self.handler.stop()
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("MQTT input layer stopped")
    
    async def _on_ingress_event(self, event: IngressEvent):
        """Handle ingress event"""
        try:
            self._increment_processed()
            await self.mapping_layer_callback(event)
        except Exception as e:
            self._increment_errors()
            self.logger.error("Error handling ingress event", 
                            trace_id=event.trace_id, 
                            error=str(e))
