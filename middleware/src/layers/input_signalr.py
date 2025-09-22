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
            
            # Register connection event handlers
            self.connection.on_open(lambda: self.logger.debug("SignalR input connection opened"))
            self.connection.on_close(lambda: self._on_connection_close())
            self.connection.on_error(lambda data: self.logger.error("SignalR input connection error", error=data))
            
            # Wait a moment for SignalR hub to be fully ready
            import time
            time.sleep(3)
            
            # Start connection
            self.connection.start()
            
            # Wait for connection to stabilize
            time.sleep(2)
            
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
            raise
    
    async def stop(self):
        """Stop SignalR connection"""
        self.is_running = False
        if self.connection:
            try:
                # Leave group (ignore errors)
                try:
                    self.connection.send("LeaveGroup", [self.config.group])
                except:
                    pass  # Ignore leave group errors
                
                # Stop connection (ignore errors)
                try:
                    self.connection.stop()
                except:
                    pass  # Ignore stop errors
                    
            except Exception as e:
                # Silent error handling for shutdown
                pass
        self.logger.info("SignalR connection stopped")
    
    def _on_message(self, *args):
        """Handle incoming SignalR message"""
        try:
            # SignalR messages come as a list of arguments
            if not args or len(args) < 1:
                return
            
            # First argument should be the message content
            message = args[0]
            
            # Parse message
            if isinstance(message, str):
                payload = json.loads(message)
            elif isinstance(message, list) and len(message) > 0:
                # If message is a list, take the first element
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
            import asyncio
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
    
    def _on_connection_close(self):
        """Handle connection close - attempt reconnection"""
        self.logger.warning("SignalR input connection closed, attempting reconnection...")
        # Schedule reconnection attempt
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._attempt_reconnection())
        except RuntimeError:
            pass
    
    async def _attempt_reconnection(self):
        """Attempt to reconnect SignalR connection"""
        try:
            self.logger.info("Attempting to reconnect SignalR input connection...")
            await self.start()
            self.logger.info("SignalR input connection reconnected successfully")
        except Exception as e:
            self.logger.error("Failed to reconnect SignalR input connection", error=str(e))
            # Schedule another attempt after delay
            import asyncio
            await asyncio.sleep(5)  # Wait 5 seconds before next attempt
            if self.is_running:
                await self._attempt_reconnection()


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