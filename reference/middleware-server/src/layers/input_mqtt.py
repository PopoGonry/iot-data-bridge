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
                # Subscribe to topic
                await self.client.subscribe(self.config.topic, qos=self.config.qos)
                
                async for message in self.client.messages:
                    if not self.is_running:
                        break
                    
                    try:
                        await self._process_message(message)
                    except Exception as e:
                        pass
                        
        except Exception as e:
            raise
    
    async def stop(self):
        """Stop MQTT client"""
        self.is_running = False
        # MQTT client will be closed when exiting the async with context
    
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
            
        except Exception as e:
            pass


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
            
            if not self.config.mqtt:
                raise ValueError("MQTT configuration is required")
            
            self.handler = MQTTInputHandler(
                self.config.mqtt,
                self._on_ingress_event
            )
            
            # Start handler in background task
            self._task = asyncio.create_task(self.handler.start())
            self.is_running = True
            
            
        except Exception as e:
            raise
    
    async def stop(self):
        """Stop input layer"""
        self.is_running = False
        
        if self.handler:
            await self.handler.stop()
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
    
    async def process_raw_data(self, raw_data: dict, meta: dict) -> Optional[Any]:
        """Process raw input data"""
        try:
            # Generate trace ID
            trace_id = str(uuid.uuid4())
            
            # Create ingress event
            ingress_event = IngressEvent(
                trace_id=trace_id,
                raw=raw_data,
                meta=meta
            )
            
            return ingress_event
            
        except Exception as e:
            return None
    
    async def _on_ingress_event(self, event: IngressEvent):
        """Handle ingress event"""
        try:
            self._increment_processed()
            await self.mapping_layer_callback(event)
        except Exception as e:
            self._increment_error()
