"""
Transport Layer - SignalR External data transmission
"""

import asyncio
import json
import uuid
import datetime
from typing import Optional, Callable, Any, Dict, List
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

from layers.base import TransportLayerInterface
from models.events import ResolvedEvent
from models.config import TransportConfig


class SignalRTransportHandler:
    """SignalR transport handler with optimized connection pooling and batch processing"""
    
    def __init__(self, config, device_catalog):
        self.config = config
        self.device_catalog = device_catalog
        self.logger = structlog.get_logger("signalr_transport")
        self.connections: Dict[str, BaseHubConnection] = {}
        self._connection_lock = asyncio.Lock()
        self.is_running = False
        
    async def start(self):
        """Start SignalR transport handler"""
        if not SIGNALR_AVAILABLE:
            self.logger.error("SignalR is not available. Please install signalrcore library.")
            raise ImportError("SignalR library not available")
        
        self.is_running = True
        self.logger.info("SignalR transport handler started")
    
    async def stop(self):
        """Stop SignalR transport handler"""
        self.is_running = False
        
        # Close all connections
        for device_id, connection in self.connections.items():
            try:
                connection.stop()
                self.logger.debug("SignalR connection closed", device=device_id)
            except Exception as e:
                self.logger.error("Error closing SignalR connection", device=device_id, error=str(e))
        
        self.connections.clear()
        self.logger.info("SignalR transport handler stopped")
    
    async def _ensure_connection(self, device_id: str) -> Optional[BaseHubConnection]:
        """Ensure connection exists for device with connection pooling"""
        if device_id in self.connections:
            connection = self.connections[device_id]
            # Check if connection is still active
            if hasattr(connection, 'transport') and hasattr(connection.transport, '_ws'):
                if connection.transport._ws and connection.transport._ws.sock:
                    return connection
        
        async with self._connection_lock:
            # Double-check after acquiring lock
            if device_id in self.connections:
                connection = self.connections[device_id]
                if hasattr(connection, 'transport') and hasattr(connection.transport, '_ws'):
                    if connection.transport._ws and connection.transport._ws.sock:
                        return connection
            
            # Create new connection
            try:
                device_config = self.device_catalog.get_device(device_id)
                if not device_config:
                    self.logger.error("Device not found in catalog", device=device_id)
                    return None
                
                # Build connection with optimized settings
                connection = HubConnectionBuilder() \
                    .with_url(device_config.signalr.url) \
                    .with_automatic_reconnect([0, 2000, 10000, 30000]) \
                    .build()
                
                # Register connection event handlers
                connection.on_open(lambda: self.logger.debug("SignalR connection opened", device=device_id))
                connection.on_close(lambda: self.logger.debug("SignalR connection closed", device=device_id))
                connection.on_error(lambda data: self.logger.error("SignalR connection error", device=device_id, error=data))
                
                # Start connection
                connection.start()
                
                # Wait for connection to stabilize
                await asyncio.sleep(1)
                
                # Join group
                connection.send("JoinGroup", [device_config.signalr.group])
                
                # Store connection
                self.connections[device_id] = connection
                
                self.logger.info("SignalR connection established", device=device_id)
                return connection
                
            except Exception as e:
                self.logger.error("Failed to establish SignalR connection", device=device_id, error=str(e))
                return None
    
    async def send_to_device(self, device_id: str, event: ResolvedEvent) -> bool:
        """Send event to specific device"""
        try:
            connection = await self._ensure_connection(device_id)
            if not connection:
                return False
            
            # Prepare message
            message = {
                "trace_id": event.trace_id,
                "data": event.data,
                "meta": event.meta,
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
            
            # Send message
            connection.send("SendMessage", [device_config.signalr.group, "ingress", json.dumps(message)])
            
            self.logger.debug("SignalR message sent", device=device_id, trace_id=event.trace_id)
            return True
            
        except Exception as e:
            self.logger.error("Error sending SignalR message", device=device_id, error=str(e))
            return False
    
    async def send_batch_to_devices(self, device_events: Dict[str, List[ResolvedEvent]]) -> Dict[str, bool]:
        """Send batch of events to multiple devices"""
        results = {}
        
        # Process devices in parallel
        tasks = []
        for device_id, events in device_events.items():
            if not events:
                results[device_id] = True
                continue
            
            task = asyncio.create_task(self._send_batch_to_device(device_id, events))
            tasks.append((device_id, task))
        
        # Wait for all tasks to complete
        for device_id, task in tasks:
            try:
                results[device_id] = await task
            except Exception as e:
                self.logger.error("Error in batch send task", device=device_id, error=str(e))
                results[device_id] = False
        
        return results
    
    async def _send_batch_to_device(self, device_id: str, events: List[ResolvedEvent]) -> bool:
        """Send batch of events to a single device"""
        try:
            connection = await self._ensure_connection(device_id)
            if not connection:
                return False
            
            # Prepare batch messages
            batch_messages = []
            for event in events:
                message = {
                    "trace_id": event.trace_id,
                    "data": event.data,
                    "meta": event.meta,
                    "timestamp": datetime.datetime.utcnow().isoformat()
                }
                batch_messages.append(message)
            
            # Send batch
            device_config = self.device_catalog.get_device(device_id)
            if device_config:
                connection.send("SendBatchMessages", [
                    device_config.signalr.group, 
                    "ingress", 
                    json.dumps(batch_messages)
                ])
            
            self.logger.debug("SignalR batch sent", device=device_id, count=len(events))
            return True
            
        except Exception as e:
            self.logger.error("Error sending SignalR batch", device=device_id, error=str(e))
            return False
    
    async def send_to_devices(self, events: List[ResolvedEvent]) -> Dict[str, bool]:
        """Send events to target devices with optimized batch processing"""
        if not events:
            return {}
        
        # Group events by device
        device_events = {}
        for event in events:
            device_id = event.meta.get('target_device')
            if device_id:
                if device_id not in device_events:
                    device_events[device_id] = []
                device_events[device_id].append(event)
        
        # Try batch processing first
        if len(device_events) > 1:
            batch_results = await self.send_batch_to_devices(device_events)
            if all(batch_results.values()):
                return batch_results
        
        # Fallback to individual sends in parallel
        tasks = []
        for device_id, device_events_list in device_events.items():
            for event in device_events_list:
                task = asyncio.create_task(self.send_to_device(device_id, event))
                tasks.append((device_id, task))
        
        # Wait for all tasks to complete
        results = {}
        for device_id, task in tasks:
            try:
                success = await task
                if device_id not in results:
                    results[device_id] = success
                else:
                    results[device_id] = results[device_id] and success
            except Exception as e:
                self.logger.error("Error in parallel send task", device=device_id, error=str(e))
                results[device_id] = False
        
        return results


class TransportLayer(TransportLayerInterface):
    """Transport Layer - SignalR only"""
    
    def __init__(self, config: TransportConfig, device_catalog):
        super().__init__("transport_layer")
        self.config = config
        self.device_catalog = device_catalog
        self.handler = None
        self._task = None
        
        if not self.config.signalr:
            raise ValueError("SignalR configuration is required")
        self.handler = SignalRTransportHandler(self.config.signalr, device_catalog)
    
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
    
    async def send_to_devices(self, events: List[ResolvedEvent]) -> Dict[str, bool]:
        """Send events to target devices"""
        if not self.handler:
            return {}
        
        try:
            results = await self.handler.send_to_devices(events)
            
            # Update statistics
            for device_id, success in results.items():
                if success:
                    self._increment_processed()
                else:
                    self._increment_error()
            
            return results
            
        except Exception as e:
            self.logger.error("Error in transport layer", error=str(e))
            return {}