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
        self.connection_retry_count = 0
        self.max_retries = 5
        self.retry_delay = 5
    
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
            
            # Register connection event handlers
            self.connection.on_open(self._on_connection_open)
            self.connection.on_close(self._on_connection_close)
            self.connection.on_error(self._on_connection_error)
            
            # Wait a moment for SignalR hub to be fully ready
            await asyncio.sleep(3)
            
            # Start connection
            self.connection.start()
            
            # Wait for connection to stabilize
            await asyncio.sleep(2)
            
            # Check if connection is still active
            if hasattr(self.connection, 'transport') and hasattr(self.connection.transport, '_ws'):
                if self.connection.transport._ws and self.connection.transport._ws.sock:
                    pass  # Connection is active
                else:
                    raise ConnectionError("SignalR connection is not active")
            
            # Join group
            self.connection.send("JoinGroup", [self.config.group])
            
            self.is_running = True
            
        except Exception as e:
            import traceback
            print(f"SignalR connection error: {e}")
            print(f"Traceback: {traceback.format_exc()}")
            self.logger.error("SignalR connection error", error=str(e))
            self.logger.error("SignalR connection traceback", traceback=traceback.format_exc())
            
            # Try to reconnect if we haven't exceeded max retries
            if self.connection_retry_count < self.max_retries:
                self.connection_retry_count += 1
                self.logger.info(f"Attempting to reconnect... (attempt {self.connection_retry_count}/{self.max_retries})")
                await asyncio.sleep(self.retry_delay)
                return await self.start()
            else:
                self.logger.error("Max reconnection attempts exceeded")
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
    
    def _on_connection_open(self):
        """Handle connection open event"""
        self.logger.info("SignalR connection opened")
        self.connection_retry_count = 0  # Reset retry count on successful connection
    
    def _on_connection_close(self):
        """Handle connection close event"""
        self.logger.warning("SignalR connection closed")
        if self.is_running:
            # Try to reconnect if we're still supposed to be running
            asyncio.create_task(self._attempt_reconnect())
    
    def _on_connection_error(self, data):
        """Handle connection error event"""
        self.logger.error("SignalR connection error", error=data)
        if self.is_running:
            # Try to reconnect on error
            asyncio.create_task(self._attempt_reconnect())
    
    async def _attempt_reconnect(self):
        """Attempt to reconnect to SignalR hub"""
        if not self.is_running or self.connection_retry_count >= self.max_retries:
            return
        
        self.connection_retry_count += 1
        self.logger.info(f"Attempting to reconnect... (attempt {self.connection_retry_count}/{self.max_retries})")
        
        try:
            await asyncio.sleep(self.retry_delay)
            await self.start()
        except Exception as e:
            self.logger.error("Reconnection failed", error=str(e))
    
    def _on_callback_done(self, task):
        """Handle callback task completion"""
        try:
            if task.exception():
                self.logger.error("Callback task failed", error=str(task.exception()))
        except Exception as e:
            self.logger.error("Error in callback completion handler", error=str(e))
    
    def _on_message(self, *args):
        """Handle incoming SignalR message"""
        try:
            # SignalR messages come as a list of arguments
            if not args or len(args) < 1:
                return
            
            # First argument should be the message content
            message = args[0]
            
            
            # Parse message (Reference 방식)
            if isinstance(message, str):
                payload = json.loads(message)
            elif isinstance(message, list) and len(message) > 0:
                # If message is a list, take the first element (Reference 방식)
                if isinstance(message[0], str):
                    payload = json.loads(message[0])
                else:
                    payload = message[0]
            else:
                payload = message
            
            # Create ingress event
            trace_id = str(uuid.uuid4())
            ingress_event = IngressEvent(
                trace_id=trace_id,
                raw=payload,
                meta={
                    "source": "signalr",
                    "group": self.config.group,
                    "target": "ingress"
                }
            )
            
            # Schedule the callback as a task
            try:
                # Try to get the current event loop
                loop = asyncio.get_running_loop()
                loop.create_task(self.callback(ingress_event))
            except RuntimeError:
                # If no event loop is running, create a new one
                asyncio.run(self.callback(ingress_event))
            
        except json.JSONDecodeError as e:
            self.logger.error("Invalid JSON in SignalR message", error=str(e), message=message)
        except Exception as e:
            import traceback
            print(f"Error processing SignalR message: {e}")
            print(f"Message: {message}")
            print(f"Traceback: {traceback.format_exc()}")
            self.logger.error("Error processing SignalR message", error=str(e), message=message, traceback=traceback.format_exc())


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