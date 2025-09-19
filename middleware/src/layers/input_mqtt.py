"""
Input Layer - MQTT External data reception
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
                
                # Subscribe to topic
                await self.client.subscribe(self.config.topic, qos=self.config.qos)
                self.logger.info("Subscribed to topic", topic=self.config.topic)
                
                # Listen for messages
                async for message in self.client.messages:
                    if not self.is_running:
                        break
                    await self._on_message(message)
                    
        except Exception as e:
            self.logger.error("MQTT connection error", error=str(e))
            raise
    
    async def stop(self):
        """Stop MQTT client"""
        self.is_running = False
        if self.client:
            await self.client.disconnect()
        self.logger.info("MQTT client stopped")
    
    async def _on_message(self, message):
        """Handle incoming MQTT message"""
        try:
            # Parse message payload
            payload = json.loads(message.payload.decode())
            
            # Create ingress event
            event = IngressEvent(
                uuid=str(uuid.uuid4()),
                timestamp=asyncio.get_event_loop().time(),
                source='mqtt',
                topic=message.topic.value,
                payload=payload
            )
            
            # Process message
            await self._process_message(event)
            
            self.logger.debug("Processed MQTT message", 
                            topic=message.topic.value,
                            payload_size=len(message.payload))
            
        except json.JSONDecodeError as e:
            self.logger.error("Invalid JSON in MQTT message", 
                            topic=message.topic.value,
                            error=str(e))
        except Exception as e:
            self.logger.error("Error processing MQTT message", error=str(e))
    
    async def _process_message(self, event: IngressEvent):
        """Process the ingress event"""
        try:
            # Call the callback function
            if self.callback:
                await self.callback(event)
        except Exception as e:
            self.logger.error("Error in message processing callback", error=str(e))


class InputLayer(InputLayerInterface):
    """Input Layer - MQTT only"""
    
    def __init__(self, config: InputConfig, callback: Callable[[IngressEvent], None]):
        super().__init__("mqtt_input")
        self.config = config
        self.callback = callback
        self.handler = None
        
        # Initialize handler based on input type
        if self.config.type == "mqtt":
            if not self.config.mqtt:
                raise ValueError("MQTT configuration is required for MQTT input type")
            self.handler = MQTTInputHandler(
                self.config.mqtt,
                callback
            )
        else:
            raise ValueError(f"Unsupported input type: {self.config.type}")
    
    async def start(self):
        """Start input layer"""
        if self.handler:
            await self.handler.start()
        else:
            raise RuntimeError("Input handler not initialized")
    
    async def stop(self):
        """Stop input layer"""
        if self.handler:
            await self.handler.stop()
    
    async def process_raw_data(self, raw_data: dict, meta: dict) -> Optional[Any]:
        """Process raw input data"""
        try:
            # Create ingress event from raw data
            event = IngressEvent(
                uuid=str(uuid.uuid4()),
                timestamp=asyncio.get_event_loop().time(),
                source='mqtt',
                topic=meta.get('topic', 'unknown'),
                payload=raw_data
            )
            
            # Call the callback function
            if self.callback:
                await self.callback(event)
            
            self._increment_processed()
            return event
            
        except Exception as e:
            self.logger.error("Error processing raw data", error=str(e))
            self._increment_error()
            return None
