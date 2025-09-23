#!/usr/bin/env python3
"""
Input Layer - SignalR Only
"""

import asyncio
import json
import uuid
from typing import Optional, Callable, Any
import structlog

from signalrcore.hub_connection_builder import HubConnectionBuilder

from layers.base import InputLayerInterface
from models.events import IngressEvent
from models.config import InputConfig


class SignalRInputHandler:
    """SignalR input handler"""
    
    def __init__(self, config, callback: Callable[[IngressEvent], None]):
        self.config = config
        self.callback = callback
        self.logger = structlog.get_logger("signalr_input")
        self.connection = None
        self.is_running = False

    async def start(self):
        """Start SignalR connection"""
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
        self.logger.info("Stopping SignalR connection")
        self.is_running = False
        if self.connection:
            await self.connection.stop()

    async def _on_message(self, message):
        """Handle incoming SignalR message"""
        try:
            # Parse message
            if isinstance(message, str):
                payload = json.loads(message)
            else:
                payload = message
            
            # Generate trace ID
            trace_id = str(uuid.uuid4())
            
            # Create ingress event
            ingress_event = IngressEvent(
                trace_id=trace_id,
                raw=payload,
                meta={
                    "source": "signalr",
                    "group": self.config.group
                }
            )
            
            # Send to mapping layer
            await self.callback(ingress_event)
            
            self.logger.debug("Processed SignalR message", 
                            trace_id=trace_id,
                            group=self.config.group)
            
        except Exception as e:
            self.logger.error("Error processing SignalR message", error=str(e))

# ----------------------------------------
# InputLayer 구현
# ----------------------------------------
class InputLayer(InputLayerInterface):
    """Input Layer - SignalR only"""

    def __init__(self, config: InputConfig, mapping_layer_callback: Callable[[IngressEvent], None]):
        super().__init__("input_layer")
        self.config = config
        self.mapping_layer_callback = mapping_layer_callback
        self.handler = None

        if not self.config.signalr:
            raise ValueError("SignalR configuration is required")
        self.handler = SignalRInputHandler(self.config.signalr, self._on_ingress_event)

    async def start(self):
        await self.handler.start()
        self.is_running = True

    async def stop(self):
        self.is_running = False
        if self.handler:
            await self.handler.stop()

    async def _on_ingress_event(self, event: IngressEvent):
        self._increment_processed()
        await self.mapping_layer_callback(event)
