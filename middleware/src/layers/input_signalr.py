"""
Input Layer - SignalR External data reception (Optimized)
"""

import asyncio
import json
import uuid
from typing import Optional, Callable, Any, Dict, List
import structlog
from collections import deque
import weakref

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


class SignalRConnectionPool:
    """SignalR connection pool for better performance"""
    
    def __init__(self, config, max_connections: int = 5):
        self.config = config
        self.max_connections = max_connections
        self.connections: deque = deque()
        self.active_connections = 0
        self.logger = structlog.get_logger("signalr_pool")
        
    async def get_connection(self) -> BaseHubConnection:
        """Get a connection from pool or create new one"""
        if self.connections:
            return self.connections.popleft()
        
        if self.active_connections < self.max_connections:
            connection = await self._create_connection()
            self.active_connections += 1
            return connection
        
        # Wait for available connection
        while not self.connections:
            await asyncio.sleep(0.01)
        return self.connections.popleft()
    
    async def return_connection(self, connection: BaseHubConnection):
        """Return connection to pool"""
        if connection and self._is_connection_healthy(connection):
            self.connections.append(connection)
        else:
            self.active_connections -= 1
    
    async def _create_connection(self) -> BaseHubConnection:
        """Create new SignalR connection"""
        connection = HubConnectionBuilder() \
            .with_url(self.config.url) \
            .build()
        
        # Optimized connection setup
        connection.on_open(lambda: self.logger.debug("SignalR connection opened"))
        connection.on_close(lambda: self.logger.debug("SignalR connection closed"))
        connection.on_error(lambda data: self.logger.error("SignalR connection error", error=data))
        
        connection.start()
        
        # Non-blocking wait for connection
        await asyncio.sleep(0.5)
        
        # Join group
        connection.send("JoinGroup", [self.config.group])
        
        return connection
    
    def _is_connection_healthy(self, connection: BaseHubConnection) -> bool:
        """Check if connection is still healthy"""
        try:
            if hasattr(connection, 'transport') and hasattr(connection.transport, '_ws'):
                return connection.transport._ws and connection.transport._ws.sock
            return False
        except:
            return False
    
    async def close_all(self):
        """Close all connections in pool"""
        for connection in self.connections:
            try:
                connection.send("LeaveGroup", [self.config.group])
                connection.stop()
            except:
                pass
        self.connections.clear()
        self.active_connections = 0


class SignalRInputHandler:
    """Optimized SignalR input handler with connection pooling and batch processing"""
    
    def __init__(self, config, callback: Callable[[IngressEvent], None]):
        self.config = config
        self.callback = callback
        self.logger = structlog.get_logger("signalr_input")
        self.connection_pool = SignalRConnectionPool(config, max_connections=3)
        self.is_running = False
        self.message_queue = deque(maxlen=1000)  # Message queue for batch processing
        self.batch_size = 10
        self.batch_timeout = 0.1  # 100ms batch timeout
        self._batch_task = None
        
    async def start(self):
        """Start SignalR connection with optimized setup"""
        if not SIGNALR_AVAILABLE:
            self.logger.error("SignalR is not available. Please install signalrcore library.")
            raise ImportError("SignalR library not available")
            
        try:
            # Get connection from pool
            self.connection = await self.connection_pool.get_connection()
            
            # Register optimized message handler
            self.connection.on("ingress", self._on_message)
            
            # Start batch processing task
            self._batch_task = asyncio.create_task(self._process_batch_messages())
            
            self.is_running = True
            # Silent startup
            
        except Exception as e:
            self.logger.error("SignalR connection error", error=str(e))
            raise
    
    async def stop(self):
        """Stop SignalR connection and cleanup"""
        self.is_running = False
        
        # Cancel batch processing
        if self._batch_task:
            self._batch_task.cancel()
            try:
                await self._batch_task
            except asyncio.CancelledError:
                pass
        
        # Return connection to pool
        if hasattr(self, 'connection'):
            await self.connection_pool.return_connection(self.connection)
        
        # Close all connections
        await self.connection_pool.close_all()
        
        self.logger.info("SignalR input handler stopped")
    
    def _on_message(self, *args):
        """Handle incoming SignalR message - optimized for batch processing"""
        try:
            if not args or len(args) < 1:
                return
            
            message = args[0]
            
            # Parse message efficiently
            if isinstance(message, str):
                try:
                    payload = json.loads(message)
                except json.JSONDecodeError:
                    return
            elif isinstance(message, list) and len(message) > 0:
                if isinstance(message[0], str):
                    try:
                        payload = json.loads(message[0])
                    except json.JSONDecodeError:
                        return
                else:
                    payload = message[0]
            else:
                payload = message
            
            # Add to message queue for batch processing
            self.message_queue.append(payload)
            
        except Exception as e:
            self.logger.error("Error processing SignalR message", error=str(e))
    
    async def _process_batch_messages(self):
        """Process messages in batches for better performance"""
        while self.is_running:
            try:
                if not self.message_queue:
                    await asyncio.sleep(self.batch_timeout)
                    continue
                
                # Collect batch of messages
                batch = []
                for _ in range(min(self.batch_size, len(self.message_queue))):
                    if self.message_queue:
                        batch.append(self.message_queue.popleft())
                
                if batch:
                    # Process batch asynchronously
                    await self._process_message_batch(batch)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Error in batch processing", error=str(e))
                await asyncio.sleep(0.1)
    
    async def _process_message_batch(self, batch: List[Dict]):
        """Process a batch of messages efficiently"""
        tasks = []
        
        for payload in batch:
            try:
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
                
                # Create task for callback
                task = asyncio.create_task(self.callback(ingress_event))
                tasks.append(task)
                
            except Exception as e:
                self.logger.error("Error creating ingress event", error=str(e))
        
        # Wait for all tasks to complete
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


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