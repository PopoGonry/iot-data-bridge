"""
Transports Layer - SignalR Sends resolved events to target devices
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Optional, Callable, List, Any
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

from layers.base import TransportsLayerInterface
from models.events import ResolvedEvent, TransportEvent, DeviceTarget, TransportConfig, TransportType, DeviceIngestLog, LayerResult
from models.config import TransportsConfig
from catalogs.device_catalog import DeviceCatalog


class SignalRTransport:
    """SignalR transport handler"""
    
    def __init__(self, config):
        self.config = config
        self.logger = structlog.get_logger("signalr_transport")
        self.connection: Optional[BaseHubConnection] = None
        self.is_connected = False
    
    async def _ensure_connection(self) -> bool:
        """Ensure SignalR connection is established"""
        try:
            if not self.connection or not self.is_connected:
                self.logger.info("Establishing SignalR transport connection...")
                
                self.connection = HubConnectionBuilder() \
                    .with_url(self.config.url) \
                    .build()
                
                # Add event handlers to prevent undefined errors
                self.connection.on_open(lambda: self.logger.debug("SignalR transport connection opened"))
                self.connection.on_close(lambda: self._on_connection_close())
                self.connection.on_error(lambda data: self.logger.error("SignalR transport connection error", error=data))
                
                self.connection.start()
                
                # Wait for connection to stabilize
                import time
                time.sleep(1)
                
                # Check if connection is active
                if hasattr(self.connection, 'transport') and hasattr(self.connection.transport, '_ws'):
                    if self.connection.transport._ws and self.connection.transport._ws.sock:
                        self.is_connected = True
                        self.logger.info("SignalR transport connection established successfully")
                        return True
                    else:
                        self.logger.error("SignalR transport connection failed to establish")
                        return False
                else:
                    self.logger.error("SignalR transport connection verification failed")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error("Error establishing SignalR transport connection", error=str(e))
            self.is_connected = False
            return False
    
    def _on_connection_close(self):
        """Handle connection close"""
        self.logger.warning("SignalR transport connection closed")
        self.is_connected = False
    
    async def send_to_device(self, device_target: DeviceTarget) -> bool:
        """Send data to device via SignalR"""
        try:
            # Ensure connection is established
            if not await self._ensure_connection():
                return False
            
            # Get device-specific configuration
            device_config = device_target.transport_config.config
            group = device_config.get('group', device_target.device_id)
            target = device_config.get('target', 'ingress')
            
            # Prepare payload
            payload = {
                "object": device_target.object,
                "value": device_target.value,
                "timestamp": asyncio.get_event_loop().time()
            }
            
            # Send message to device group
            self.connection.send("SendMessage", [group, target, json.dumps(payload)])
            
            return True
            
        except Exception as e:
            self.logger.error("Error sending SignalR message",
                            device_id=device_target.device_id,
                            error=str(e))
            # Mark connection as disconnected on error
            self.is_connected = False
            return False
    
    async def close_connection(self):
        """Close SignalR connection"""
        if self.connection:
            try:
                # Stop connection (ignore errors during shutdown)
                try:
                    self.connection.stop()
                except:
                    pass  # Ignore stop errors during shutdown
                    
                self.logger.info("SignalR transport connection closed")
            except Exception as e:
                # Silent error handling for shutdown
                pass
            finally:
                self.connection = None
                self.is_connected = False


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
        # Establish connection at startup
        await self.transport._ensure_connection()
    
    async def stop(self) -> None:
        self.is_running = False
        # Close connection on shutdown
        await self.transport.close_connection()
    
    async def send_to_devices(self, event: ResolvedEvent) -> LayerResult:
        self._increment_processed()
        
        try:
            # Prepare all device targets
            device_targets = []
            for device_id in event.target_devices:
                transport_config = TransportConfig(
                    type=TransportType.SIGNALR,
                    config={'group': device_id, 'target': 'ingress'}
                )
                device_target = DeviceTarget(device_id=device_id, transport_config=transport_config, object=event.object, value=event.value)
                device_targets.append(device_target)
            
            # Send to all devices using batch transmission
            success_count = await self._send_batch_to_devices(device_targets, event.trace_id)
            
            return LayerResult(
                success=success_count > 0, 
                processed_count=len(device_targets), 
                error_count=len(device_targets) - success_count, 
                data=device_targets
            )
            
        except Exception as e:
            self.logger.error("TRANSPORTS LAYER: Critical error in send_to_devices",
                            trace_id=event.trace_id,
                            error=str(e))
            import traceback
            self.logger.error("TRANSPORTS LAYER: Traceback", traceback=traceback.format_exc())
            return LayerResult(success=False, processed_count=0, error_count=1, data=[])
    
    async def _send_batch_to_devices(self, device_targets: list, trace_id: str) -> int:
        """Send batch messages to multiple devices efficiently"""
        success_count = 0
        
        try:
            # Ensure connection is established
            if not await self.transport._ensure_connection():
                self.logger.error("TRANSPORTS LAYER: Failed to establish connection for batch send")
                return 0
            
            # Prepare batch messages for each device group
            device_groups = {}
            for device_target in device_targets:
                device_config = device_target.transport_config.config
                group = device_config.get('group', device_target.device_id)
                target = device_config.get('target', 'ingress')
                
                if group not in device_groups:
                    device_groups[group] = []
                
                payload = {
                    "object": device_target.object,
                    "value": device_target.value,
                    "timestamp": asyncio.get_event_loop().time()
                }
                
                device_groups[group].append({
                    'device_id': device_target.device_id,
                    'payload': payload,
                    'target': target
                })
            
            # Send batch messages to each group
            for group, messages in device_groups.items():
                try:
                    # Prepare batch payload
                    batch_payloads = [msg['payload'] for msg in messages]
                    
                    # Send batch message to group
                    self.transport.connection.send("SendBatchMessages", [group, "ingress", json.dumps(batch_payloads)])
                    
                    # Log successful sends
                    for msg in messages:
                        success_count += 1
                        
                        # Log device ingest
                        ingest_log = DeviceIngestLog(
                            trace_id=trace_id,
                            device_id=msg['device_id'],
                            object=msg['payload']['object'],
                            value=msg['payload']['value']
                        )
                        await self.device_ingest_callback(ingest_log)
                    
                    self.logger.debug(f"TRANSPORTS LAYER: Batch sent to group {group}", 
                                    message_count=len(messages),
                                    trace_id=trace_id)
                    
                except Exception as e:
                    self.logger.error(f"TRANSPORTS LAYER: Failed to send batch to group {group}",
                                    error=str(e),
                                    trace_id=trace_id)
                    
                    # Fallback to individual messages
                    for msg in messages:
                        try:
                            self.transport.connection.send("SendMessage", [group, msg['target'], json.dumps(msg['payload'])])
                            success_count += 1
                            
                            # Log device ingest
                            ingest_log = DeviceIngestLog(
                                trace_id=trace_id,
                                device_id=msg['device_id'],
                                object=msg['payload']['object'],
                                value=msg['payload']['value']
                            )
                            await self.device_ingest_callback(ingest_log)
                            
                        except Exception as e2:
                            self.logger.warning(f"TRANSPORTS LAYER: Failed to deliver to device {msg['device_id']}",
                                              error=str(e2),
                                              trace_id=trace_id)
            
            return success_count
            
        except Exception as e:
            self.logger.error("TRANSPORTS LAYER: Error in batch send",
                            error=str(e),
                            trace_id=trace_id)
            return 0