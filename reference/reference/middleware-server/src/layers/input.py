"""
Input Layer - External data reception (MQTT/SignalR)
"""

import asyncio
import json
import uuid
from typing import Optional, Callable, Any
import structlog

from aiomqtt import Client as MQTTClient

# SignalR import (optional)
try:
    from signalrcore import HubConnectionBuilder
    SIGNALR_AVAILABLE = True
except ImportError:
    SIGNALR_AVAILABLE = False
    HubConnectionBuilder = None

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
                        self.logger.error("Error processing MQTT message", error=str(e))
                        
        except Exception as e:
            self.logger.error("MQTT client error", error=str(e))
            raise
    
    async def stop(self):
        """Stop MQTT client"""
        self.is_running = False
        if self.client:
            await self.client.disconnect()
        self.logger.info("MQTT client stopped")
    
    async def _process_message(self, message):
        """Process incoming MQTT message"""
        try:
            # Parse JSON payload
            payload = json.loads(message.payload.decode('utf-8'))
            
            # Extract trace_id from header or generate new one
            trace_id = payload.get('header', {}).get('UUID', str(uuid.uuid4()))
            
            # Create metadata
            meta = {
                'source': 'mqtt',
                'topic': message.topic,
                'qos': message.qos,
                'retain': message.retain,
                'timestamp': asyncio.get_event_loop().time()
            }
            
            # Create IngressEvent
            ingress_event = IngressEvent(
                trace_id=trace_id,
                raw=payload,
                meta=meta
            )
            
            # Call callback
            await self.callback(ingress_event)
            
            self.logger.debug("Processed MQTT message", 
                            trace_id=trace_id,
                            topic=message.topic)
            
        except json.JSONDecodeError as e:
            self.logger.error("Invalid JSON in MQTT message", error=str(e))
        except Exception as e:
            self.logger.error("Error processing MQTT message", error=str(e))


class SignalRInputHandler:
    """SignalR input handler"""
    
    def __init__(self, config, callback: Callable[[IngressEvent], None]):
        if not SIGNALR_AVAILABLE:
            raise ImportError("SignalR not available. Install signalrcore package.")
        
        self.config = config
        self.callback = callback
        self.logger = structlog.get_logger("signalr_input")
        self.connection = None
        self.is_running = False
    
    async def start(self):
        """Start SignalR connection"""
        if not SIGNALR_AVAILABLE:
            raise ImportError("SignalR not available. Install signalrcore package.")
            
        try:
            # Build connection
            builder = HubConnectionBuilder()
            builder.with_url(self.config.url)
            
            if self.config.username and self.config.password:
                builder.with_authentication(self.config.username, self.config.password)
            
            self.connection = builder.build()
            
            # Register message handler
            self.connection.on("ReceiveMessage", self._on_message)
            
            # Start connection
            await self.connection.start()
            self.is_running = True
            
            # Join group
            await self.connection.invoke("JoinGroup", self.config.group)
            
            self.logger.info("SignalR connection started", 
                           url=self.config.url,
                           group=self.config.group)
            
            # Keep connection alive
            while self.is_running:
                await asyncio.sleep(1)
                
        except Exception as e:
            self.logger.error("SignalR connection error", error=str(e))
            raise
    
    async def stop(self):
        """Stop SignalR connection"""
        self.is_running = False
        if self.connection:
            await self.connection.stop()
        self.logger.info("SignalR connection stopped")
    
    async def _on_message(self, message_data):
        """Handle incoming SignalR message"""
        try:
            # Parse message data
            if isinstance(message_data, str):
                payload = json.loads(message_data)
            else:
                payload = message_data
            
            # Extract trace_id from header or generate new one
            trace_id = payload.get('header', {}).get('UUID', str(uuid.uuid4()))
            
            # Create metadata
            meta = {
                'source': 'signalr',
                'group': self.config.group,
                'timestamp': asyncio.get_event_loop().time()
            }
            
            # Create IngressEvent
            ingress_event = IngressEvent(
                trace_id=trace_id,
                raw=payload,
                meta=meta
            )
            
            # Call callback
            await self.callback(ingress_event)
            
            self.logger.debug("Processed SignalR message", 
                            trace_id=trace_id,
                            group=self.config.group)
            
        except Exception as e:
            self.logger.error("Error processing SignalR message", error=str(e))


class InputLayer(InputLayerInterface):
    """Input Layer - Handles external data reception"""
    
    def __init__(self, config: InputConfig, mapping_layer_callback: Callable[[IngressEvent], None]):
        super().__init__("input_layer")
        self.config = config
        self.mapping_layer_callback = mapping_layer_callback
        self.handler = None
        self._task = None
    
    async def start(self):
        """Start input layer"""
        try:
            self.logger.info("Starting input layer", type=self.config.type)
            
            if self.config.type == "mqtt":
                if not self.config.mqtt:
                    raise ValueError("MQTT configuration is required for MQTT input type")
                
                self.handler = MQTTInputHandler(
                    self.config.mqtt,
                    self._on_ingress_event
                )
                
            elif self.config.type == "signalr":
                if not SIGNALR_AVAILABLE:
                    raise ImportError("SignalR not available. Install signalrcore package.")
                
                if not self.config.signalr:
                    raise ValueError("SignalR configuration is required for SignalR input type")
                
                self.handler = SignalRInputHandler(
                    self.config.signalr,
                    self._on_ingress_event
                )
                
            else:
                raise ValueError(f"Unsupported input type: {self.config.type}")
            
            # Start handler in background task
            self._task = asyncio.create_task(self.handler.start())
            self.is_running = True
            
            self.logger.info("Input layer started successfully")
            
        except Exception as e:
            self.logger.error("Failed to start input layer", error=str(e))
            raise
    
    async def stop(self):
        """Stop input layer"""
        self.logger.info("Stopping input layer")
        self.is_running = False
        
        if self.handler:
            await self.handler.stop()
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Input layer stopped")
    
    async def process_raw_data(self, raw_data: dict, meta: dict) -> Optional[IngressEvent]:
        """Process raw input data (for testing purposes)"""
        try:
            trace_id = raw_data.get('header', {}).get('UUID', str(uuid.uuid4()))
            
            ingress_event = IngressEvent(
                trace_id=trace_id,
                raw=raw_data,
                meta=meta
            )
            
            await self._on_ingress_event(ingress_event)
            return ingress_event
            
        except Exception as e:
            self.logger.error("Error processing raw data", error=str(e))
            return None
    
    async def _on_ingress_event(self, event: IngressEvent):
        """Handle ingress event and forward to mapping layer"""
        try:
            self._increment_processed()
            
            self.logger.debug("Received ingress event", 
                            trace_id=event.trace_id,
                            source=event.meta.get('source'))
            
            # Forward to mapping layer
            await self.mapping_layer_callback(event)
            
        except Exception as e:
            self._increment_error()
            self.logger.error("Error handling ingress event", 
                            error=str(e), 
                            trace_id=event.trace_id)
