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
            self.logger.info("🔌 CONNECTING TO MQTT BROKER",
                           host=self.config.host,
                           port=self.config.port,
                           topic=self.config.topic)
            
            self.client = MQTTClient(
                hostname=self.config.host,
                port=self.config.port,
                username=self.config.username,
                password=self.config.password,
                keepalive=self.config.keepalive
            )
            
            async with self.client:
                self.is_running = True
                self.logger.info("✅ MQTT CLIENT CONNECTED", 
                               host=self.config.host, 
                               port=self.config.port,
                               topic=self.config.topic)
                
                # Subscribe to topic
                self.logger.info("📡 TOPIC 구독 시작", topic=self.config.topic, qos=self.config.qos)
                await self.client.subscribe(self.config.topic, qos=self.config.qos)
                self.logger.info("✅ TOPIC 구독 완료", topic=self.config.topic)
                
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
        # MQTT client will be closed when exiting the async with context
    
    async def _process_message(self, message):
        """Process incoming MQTT message"""
        try:
            self.logger.info("📨 MQTT 메시지 수신",
                           topic=message.topic,
                           size=len(message.payload),
                           qos=message.qos)
            
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
            
            self.logger.info("📥 데이터 파싱 완료",
                           trace_id=trace_id,
                           equip_tag=payload.get('payload', {}).get('Equip.Tag'),
                           message_id=payload.get('payload', {}).get('Message.ID'))
            
            # Send to mapping layer
            await self.callback(ingress_event)
            
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
            self.logger.error("Error processing raw data", error=str(e))
            return None
    
    async def _on_ingress_event(self, event: IngressEvent):
        """Handle ingress event"""
        try:
            self._increment_processed()
            await self.mapping_layer_callback(event)
        except Exception as e:
            self._increment_error()
            self.logger.error("Error handling ingress event", 
                            trace_id=event.trace_id, 
                            error=str(e))
