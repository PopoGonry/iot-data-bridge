"""
Input Layer - SignalR External data reception
"""

import asyncio
import json
import uuid
from typing import Optional, Callable, Any
import structlog

try:
    from signalrcore.hub_connection_builder import HubConnectionBuilder
    from signalrcore.hub.base_hub_connection import BaseHubConnection
    SIGNALR_AVAILABLE = True
except ImportError as e:
    print(f"SignalR import error: {e}")
    SIGNALR_AVAILABLE = False
    HubConnectionBuilder = None
    BaseHubConnection = None

from layers.base import InputLayerInterface
from models.events import IngressEvent
from models.config import InputConfig


class SignalRInputHandler:
    """SignalR input handler"""
    
    def __init__(self, config, callback: Callable[[IngressEvent], None]):
        self.config = config
        self.callback = callback
        self.logger = structlog.get_logger("signalr_input")
        self.connection: Optional[BaseHubConnection] = None
        self.is_running = False
    
    async def start(self):
        """Start SignalR connection"""
        if not SIGNALR_AVAILABLE:
            self.logger.error("SignalR is not available. Please install signalrcore library.")
            raise ImportError("SignalR library not available")
            
        try:
            # Build connection
            self.connection = HubConnectionBuilder() \
                .with_url(self.config.url) \
                .build()
            
            # Register message handler for ingress messages
            self.connection.on("ingress", self._on_message)
            
            # Start connection
            self.connection.start()
            
            # Join group
            self.connection.send("JoinGroup", [self.config.group])
            self.logger.info("Attempting to join group", group=self.config.group)
            
            self.is_running = True
            self.logger.info("SignalR connection started", 
                           url=self.config.url,
                           group=self.config.group)
            
        except Exception as e:
            self.logger.error("SignalR connection error", error=str(e))
            raise
    
    async def stop(self):
        """Stop SignalR connection"""
        self.is_running = False
        if self.connection:
            try:
                # Leave group
                self.connection.send("LeaveGroup", [self.config.group])
                self.connection.stop()
            except Exception as e:
                self.logger.error("Error stopping SignalR connection", error=str(e))
        self.logger.info("SignalR connection stopped")
    
    async def _on_message(self, group: str, target: str, message: str):
        """Handle incoming SignalR message"""
        self.logger.info("Received SignalR message", group=group, target=target, message_length=len(str(message)))
        try:
            # Parse message
            if isinstance(message, str):
                payload = json.loads(message)
            else:
                payload = message
            
            # Create ingress event
            trace_id = str(uuid.uuid4())
            ingress_event = IngressEvent(
                trace_id=trace_id,
                raw=payload,
                meta={
                    "source": "signalr",
                    "group": group,
                    "target": target
                }
            )
            
            await self.callback(ingress_event)
            
        except json.JSONDecodeError as e:
            self.logger.error("Invalid JSON in SignalR message", error=str(e))
        except Exception as e:
            self.logger.error("Error processing SignalR message", error=str(e))


class InputLayer(InputLayerInterface):
    """Input Layer - SignalR only"""
    
    def __init__(self, config: InputConfig, mapping_layer_callback: Callable[[IngressEvent], None]):
        super().__init__("input_layer")
        self.config = config
        self.mapping_layer_callback = mapping_layer_callback
        self.handler = None
        self._task = None
        
        if not self.config.signalr:
            raise ValueError("SignalR configuration is required")
        self.handler = SignalRInputHandler(self.config.signalr, self._on_ingress_event)
    
    async def start(self):
        self._task = asyncio.create_task(self.handler.start())
        self.is_running = True
    
    async def stop(self):
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
        trace_id = str(uuid.uuid4())
        ingress_event = IngressEvent(trace_id=trace_id, raw=raw_data, meta=meta)
        return ingress_event
    
    async def _on_ingress_event(self, event: IngressEvent):
        self._increment_processed()
        await self.mapping_layer_callback(event)