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
    
    async def send_to_device(self, device_target: DeviceTarget) -> bool:
        """Send data to device via SignalR"""
        try:
            # Check if connection exists and is active
            if not self.connection or not self._is_connection_active():
                # Clean up old connection if exists
                if self.connection:
                    self.logger.info("Cleaning up old SignalR transport connection...")
                    try:
                        self.connection.stop()
                    except:
                        pass
                    self.connection = None
                
                self.logger.info("Creating new SignalR transport connection...")
                self.connection = HubConnectionBuilder() \
                    .with_url(self.config.url) \
                    .build()
                
                # Add event handlers to prevent undefined errors
                self.connection.on_open(lambda: self.logger.debug("SignalR transport connection opened"))
                self.connection.on_close(lambda: self.logger.debug("SignalR transport connection closed"))
                self.connection.on_error(lambda data: self.logger.error("SignalR transport connection error", error=data))
                
                self.connection.start()
                
                # Wait for connection to stabilize
                import time
                time.sleep(1)
            
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
            # Mark connection as invalid on error
            self.connection = None
            return False
    
    def _is_connection_active(self) -> bool:
        """Check if SignalR connection is actually active"""
        try:
            if not self.connection:
                return False
            
            # Check if connection has transport and websocket
            if hasattr(self.connection, 'transport') and hasattr(self.connection.transport, '_ws'):
                if self.connection.transport._ws and self.connection.transport._ws.sock:
                    return True
            
            return False
            
        except Exception:
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
        # Close connection on shutdown
        await self.transport.close_connection()
    
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