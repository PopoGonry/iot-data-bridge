"""
Input Layer - SignalR External data reception
"""

import asyncio
import json
import uuid
from typing import Optional, Callable, Any
import structlog

try:
    from signalrcore import HubConnection
    SIGNALR_AVAILABLE = True
except ImportError:
    SIGNALR_AVAILABLE = False
    HubConnection = None

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
        if not SIGNALR_AVAILABLE:
            self.logger.error("SignalR is not available. Please install signalrcore library.")
            raise ImportError("SignalR library not available")
            
        try:
            # Build connection
            self.connection = HubConnection(self.config.url)
            
            if self.config.username and self.config.password:
                # Note: Authentication may need to be handled differently
                # depending on the signalrcore version
                pass
            
            # Register message handler
            self.connection.on("ReceiveMessage", self._on_message)
            
            # Start connection
            await self.connection.start()
            
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
            await self.connection.stop()
        self.logger.info("SignalR connection stopped")
    
    async def _on_message(self, message):
        """Handle incoming SignalR message"""
        try:
            # Parse message
            if isinstance(message, str):
                payload = json.loads(message)
            else:
                payload = message
            
            # Create ingress event
            event = IngressEvent(
                uuid=str(uuid.uuid4()),
                timestamp=asyncio.get_event_loop().time(),
                source='signalr',
                topic=self.config.group,
                payload=payload
            )
            
            # Process message
            await self._process_message(event)
            
            self.logger.debug("Processed SignalR message", 
                            group=self.config.group,
                            payload_size=len(str(payload)))
            
        except json.JSONDecodeError as e:
            self.logger.error("Invalid JSON in SignalR message", error=str(e))
        except Exception as e:
            self.logger.error("Error processing SignalR message", error=str(e))
    
    async def _process_message(self, event: IngressEvent):
        """Process the ingress event"""
        try:
            # Call the callback function
            if self.callback:
                await self.callback(event)
        except Exception as e:
            self.logger.error("Error in message processing callback", error=str(e))


class InputLayer(InputLayerInterface):
    """Input Layer - SignalR only"""
    
    def __init__(self, config: InputConfig, callback: Callable[[IngressEvent], None]):
        super().__init__("signalr_input")
        self.config = config
        self.callback = callback
        self.handler = None
        
        # Initialize handler based on input type
        if self.config.type == "signalr":
            if not self.config.signalr:
                raise ValueError("SignalR configuration is required for SignalR input type")
            self.handler = SignalRInputHandler(
                self.config.signalr,
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
                source='signalr',
                topic=meta.get('group', 'unknown'),
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
