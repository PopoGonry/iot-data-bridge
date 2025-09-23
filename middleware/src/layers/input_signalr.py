"""
Input Layer - SignalR External data reception
"""

import asyncio
import json
import uuid
import datetime
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
    """SignalR input handler with optimized batch processing"""
    
    def __init__(self, config, callback: Callable[[IngressEvent], None]):
        self.config = config
        self.callback = callback
        self.logger = structlog.get_logger("signalr_input")
        self.connection: Optional[BaseHubConnection] = None
        self.is_running = False
        self.message_buffer = []
        self.buffer_size = 10  # Process messages in batches
        self.buffer_timeout = 1.0  # Flush buffer after 1 second
        self._buffer_task = None
    
    async def start(self):
        """Start SignalR connection with optimized settings"""
        if not SIGNALR_AVAILABLE:
            self.logger.error("SignalR is not available. Please install signalrcore library.")
            raise ImportError("SignalR library not available")
            
        try:
            # Build connection with optimized settings
            self.connection = HubConnectionBuilder() \
                .with_url(self.config.url) \
                .with_automatic_reconnect([0, 2000, 10000, 30000]) \
                .build()
            
            # Register message handler for ingress messages
            self.connection.on("ingress", self._on_message)
            
            # Register connection event handlers
            self.connection.on_open(lambda: self.logger.info("SignalR connection opened"))
            self.connection.on_close(lambda: self.logger.info("SignalR connection closed"))
            self.connection.on_error(lambda data: self.logger.error("SignalR connection error", error=data))
            
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
            
            # Start buffer processing task
            self._buffer_task = asyncio.create_task(self._process_buffer())
            
            self.is_running = True
            self.logger.info("SignalR input handler started", group=self.config.group)
            
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
        
        # Cancel buffer task
        if self._buffer_task:
            self._buffer_task.cancel()
            try:
                await self._buffer_task
            except asyncio.CancelledError:
                pass
        
        # Process remaining messages in buffer
        if self.message_buffer:
            await self._flush_buffer()
        
        if self.connection:
            try:
                # Leave group
                self.connection.send("LeaveGroup", [self.config.group])
                self.connection.stop()
            except Exception as e:
                self.logger.error("Error stopping SignalR connection", error=str(e))
        self.logger.info("SignalR connection stopped")
    
    async def _process_buffer(self):
        """Process message buffer periodically"""
        while self.is_running:
            try:
                await asyncio.sleep(self.buffer_timeout)
                if self.message_buffer:
                    await self._flush_buffer()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Error in buffer processing", error=str(e))
    
    async def _flush_buffer(self):
        """Flush message buffer and process all messages"""
        if not self.message_buffer:
            return
        
        messages = self.message_buffer.copy()
        self.message_buffer.clear()
        
        # Process messages in parallel
        tasks = []
        for message in messages:
            task = asyncio.create_task(self._process_single_message(message))
            tasks.append(task)
        
        # Wait for all tasks to complete
        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            self.logger.error("Error processing message batch", error=str(e))
    
    async def _process_single_message(self, message):
        """Process a single message with timeout protection"""
        try:
            # Create ingress event
            trace_id = str(uuid.uuid4())
            ingress_event = IngressEvent(
                trace_id=trace_id,
                raw=message,
                meta={
                    "source": "signalr",
                    "group": self.config.group,
                    "target": "ingress",
                    "timestamp": datetime.datetime.utcnow().isoformat()
                }
            )
            
            # Process with timeout
            await asyncio.wait_for(self.callback(ingress_event), timeout=5.0)
            
        except asyncio.TimeoutError:
            self.logger.warning("Message processing timed out", message=message)
        except Exception as e:
            self.logger.error("Error processing message", error=str(e), message=message)
    
    def _on_message(self, *args):
        """Handle incoming SignalR message with batch processing"""
        try:
            # SignalR messages come as a list of arguments
            if not args or len(args) < 1:
                self.logger.debug("Empty SignalR message received")
                return
            
            # First argument should be the message content
            message = args[0]
            self.logger.debug("SignalR message received", message_type=type(message).__name__)
            
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
            
            # Add to buffer
            self.message_buffer.append(payload)
            
            # If buffer is full, process immediately
            if len(self.message_buffer) >= self.buffer_size:
                asyncio.create_task(self._flush_buffer())
            
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