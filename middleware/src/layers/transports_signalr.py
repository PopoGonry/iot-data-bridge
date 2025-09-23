"""
Transports Layer - SignalR Sends resolved events to target devices (Optimized)
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Optional, Callable, List, Any, Dict
import structlog
from collections import defaultdict, deque
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

from layers.base import TransportsLayerInterface
from models.events import ResolvedEvent, TransportEvent, DeviceTarget, TransportConfig, TransportType, DeviceIngestLog, LayerResult
from models.config import TransportsConfig
from catalogs.device_catalog import DeviceCatalog


class SignalRTransportPool:
    """Optimized SignalR transport connection pool"""
    
    def __init__(self, config, max_connections: int = 10):
        self.config = config
        self.max_connections = max_connections
        self.connections: deque = deque()
        self.active_connections = 0
        self.logger = structlog.get_logger("signalr_transport_pool")
        self._connection_refs = weakref.WeakSet()
        
    async def get_connection(self) -> BaseHubConnection:
        """Get connection from pool or create new one"""
        if self.connections:
            return self.connections.popleft()
        
        if self.active_connections < self.max_connections:
            connection = await self._create_connection()
            self.active_connections += 1
            self._connection_refs.add(connection)
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
            self._connection_refs.discard(connection)
    
    async def _create_connection(self) -> BaseHubConnection:
        """Create optimized SignalR connection"""
        connection = HubConnectionBuilder() \
            .with_url(self.config.url) \
            .build()
        
        # Optimized event handlers
        connection.on_open(lambda: self.logger.debug("SignalR transport connection opened"))
        connection.on_close(lambda: self.logger.debug("SignalR transport connection closed"))
        connection.on_error(lambda data: self.logger.error("SignalR transport connection error", error=data))
        
        connection.start()
        
        # Non-blocking wait
        await asyncio.sleep(0.3)
        
        return connection
    
    def _is_connection_healthy(self, connection: BaseHubConnection) -> bool:
        """Check connection health"""
        try:
            if hasattr(connection, 'transport') and hasattr(connection.transport, '_ws'):
                return connection.transport._ws and connection.transport._ws.sock
            return False
        except:
            return False
    
    async def close_all(self):
        """Close all connections"""
        for connection in self.connections:
            try:
                connection.stop()
            except:
                pass
        self.connections.clear()
        self.active_connections = 0


class SignalRTransport:
    """Optimized SignalR transport handler with batching and connection pooling"""
    
    def __init__(self, config):
        self.config = config
        self.logger = structlog.get_logger("signalr_transport")
        self.connection_pool = SignalRTransportPool(config, max_connections=5)
        self.message_batches = defaultdict(list)  # Group messages by device group
        self.batch_size = 20
        self.batch_timeout = 0.05  # 50ms batch timeout
        self._batch_tasks = {}
        self._connection = None
        
    async def send_to_device(self, device_target: DeviceTarget) -> bool:
        """Send data to device via SignalR with batching"""
        try:
            if not self._connection:
                self._connection = await self.connection_pool.get_connection()
            
            # Get device configuration
            device_config = device_target.transport_config.config
            group = device_config.get('group', device_target.device_id)
            target = device_config.get('target', 'ingress')
            
            # Prepare payload
            payload = {
                "object": device_target.object,
                "value": device_target.value,
                "timestamp": asyncio.get_event_loop().time()
            }
            
            # Add to batch
            self.message_batches[group].append({
                'target': target,
                'payload': payload,
                'device_id': device_target.device_id
            })
            
            # Start batch processing if not already running
            if group not in self._batch_tasks:
                self._batch_tasks[group] = asyncio.create_task(
                    self._process_batch_for_group(group)
                )
            
            return True
            
        except Exception as e:
            self.logger.error("Error queuing SignalR message",
                            device_id=device_target.device_id,
                            error=str(e))
            return False
    
    async def _process_batch_for_group(self, group: str):
        """Process batched messages for a specific group"""
        try:
            while self.message_batches[group]:
                # Collect batch
                batch = []
                for _ in range(min(self.batch_size, len(self.message_batches[group]))):
                    if self.message_batches[group]:
                        batch.append(self.message_batches[group].pop(0))
                
                if batch:
                    await self._send_batch(group, batch)
                
                # Wait for more messages or timeout
                if not self.message_batches[group]:
                    await asyncio.sleep(self.batch_timeout)
                    if not self.message_batches[group]:
                        break
                        
        except Exception as e:
            self.logger.error("Error processing batch for group", group=group, error=str(e))
        finally:
            # Clean up batch task
            if group in self._batch_tasks:
                del self._batch_tasks[group]
    
    async def _send_batch(self, group: str, batch: List[Dict]):
        """Send batch of messages efficiently"""
        try:
            if len(batch) == 1:
                # Single message
                message = batch[0]
                self._connection.send("SendMessage", [
                    group, 
                    message['target'], 
                    json.dumps(message['payload'])
                ])
            else:
                # Batch message
                batch_payloads = [msg['payload'] for msg in batch]
                self._connection.send("SendBatchMessages", [
                    group,
                    batch[0]['target'],  # All messages in batch have same target
                    json.dumps(batch_payloads)
                ])
                
        except Exception as e:
            self.logger.error("Error sending batch", group=group, error=str(e))
            # Fallback to individual messages
            for message in batch:
                try:
                    self._connection.send("SendMessage", [
                        group,
                        message['target'],
                        json.dumps(message['payload'])
                    ])
                except Exception as e2:
                    self.logger.error("Error sending individual message", 
                                    device_id=message.get('device_id'), 
                                    error=str(e2))
    
    async def close(self):
        """Close transport and cleanup"""
        # Wait for all batch tasks to complete
        if self._batch_tasks:
            await asyncio.gather(*self._batch_tasks.values(), return_exceptions=True)
        
        # Return connection to pool
        if self._connection:
            await self.connection_pool.return_connection(self._connection)
        
        # Close all connections
        await self.connection_pool.close_all()


class TransportsLayer(TransportsLayerInterface):
    """Transports Layer - SignalR only"""
    
    def __init__(self, config: TransportsConfig, device_catalog: DeviceCatalog, device_ingest_callback: Callable[[DeviceIngestLog], None]):
        super().__init__("transports_layer")
        self.config = config
        self.device_catalog = device_catalog
        self.device_ingest_callback = device_ingest_callback
        self.transport = None
        self.is_running = False
        
        if not self.config.signalr:
            raise ValueError("SignalR configuration is required")
        self.transport = SignalRTransport(self.config.signalr)
    
    async def start(self) -> None:
        self.is_running = True
    
    async def stop(self) -> None:
        self.is_running = False
    
    async def send_to_devices(self, event: ResolvedEvent) -> LayerResult:
        self._increment_processed()
        device_targets = []
        for device_id in event.target_devices:
            transport_config = TransportConfig(
                type=TransportType.SIGNALR,
                config={'group': device_id, 'target': 'ingress'}
            )
            device_target = DeviceTarget(device_id=device_id, transport_config=transport_config, object=event.object, value=event.value)
            device_targets.append(device_target)
        
        success_count = 0
        for device_target in device_targets:
            try:
                success = await self.transport.send_to_device(device_target)
                if success:
                    success_count += 1
                    
                    # Log device ingest
                    ingest_log = DeviceIngestLog(
                        trace_id=event.trace_id,
                        device_id=device_target.device_id,
                        object=device_target.object,
                        value=device_target.value
                    )
                    await self.device_ingest_callback(ingest_log)
                else:
                    self.logger.warning("TRANSPORTS LAYER: Failed to deliver to device", 
                                      trace_id=event.trace_id,
                                      device_id=device_target.device_id)
                    
            except Exception as e:
                self.logger.error("TRANSPORTS LAYER: Error delivering to device",
                                trace_id=event.trace_id,
                                device_id=device_target.device_id,
                                error=str(e))
        
        return LayerResult(success=success_count > 0, processed_count=len(device_targets), error_count=len(device_targets) - success_count, data=device_targets)