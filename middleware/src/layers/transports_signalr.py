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
        print(f"[DEBUG] send_to_device START: {device_target.device_id}")
        print(f"[DEBUG] Device target details: {device_target.device_id}/{device_target.group}")
        print(f"[DEBUG] Message payload: {device_target.payload}")
        try:
            # Check if connection exists and is active
            print(f"[DEBUG] Checking connection status...")
            print(f"[DEBUG] Connection exists: {self.connection is not None}")
            if self.connection:
                print(f"[DEBUG] Connection active check: {self._is_connection_active()}")
            
            if not self.connection or not self._is_connection_active():
                print(f"[DEBUG] Creating new connection for {device_target.device_id}")
                # Clean up old connection if exists
                if self.connection:
                    print(f"[DEBUG] Cleaning up old SignalR transport connection...")
                    self.logger.info("Cleaning up old SignalR transport connection...")
                    try:
                        self.connection.stop()
                        print(f"[DEBUG] Old connection stopped successfully")
                    except Exception as e:
                        print(f"[DEBUG] Error stopping old connection (ignored): {e}")
                    self.connection = None
                
                print(f"[DEBUG] Building new SignalR transport connection to: {self.config.url}")
                self.logger.info("Creating new SignalR transport connection...")
                self.connection = HubConnectionBuilder() \
                    .with_url(self.config.url) \
                    .build()
                print(f"[DEBUG] SignalR transport connection object created: {self.connection}")
                
                # Add event handlers to prevent undefined errors
                print(f"[DEBUG] Registering transport connection event handlers")
                self.connection.on_open(lambda: print("[DEBUG] SignalR transport connection opened"))
                self.connection.on_close(lambda: print("[DEBUG] SignalR transport connection closed"))
                self.connection.on_error(lambda data: print(f"[DEBUG] SignalR transport connection error: {data}"))
                
                print(f"[DEBUG] Starting SignalR transport connection...")
                self.connection.start()
                print(f"[DEBUG] SignalR transport connection.start() called")
                
                # Wait for connection to stabilize
                print(f"[DEBUG] Waiting 1 second for transport connection to stabilize...")
                import time
                time.sleep(1)
                print(f"[DEBUG] Transport connection stabilization wait completed")
                print(f"[DEBUG] SignalR transport connection started successfully")
            
            # Get device-specific configuration
            print(f"[DEBUG] Getting device-specific configuration for: {device_target.device_id}")
            device_config = device_target.transport_config.config
            group = device_config.get('group', device_target.device_id)
            target = device_config.get('target', 'ingress')
            print(f"[DEBUG] Device config - group: {group}, target: {target}")
            
            # Prepare payload
            print(f"[DEBUG] Preparing payload for device: {device_target.device_id}")
            payload = {
                "object": device_target.object,
                "value": device_target.value,
                "timestamp": asyncio.get_event_loop().time()
            }
            print(f"[DEBUG] Payload prepared: {payload}")
            
            print(f"[DEBUG] Sending message to {group}/{target}")
            # Send message to device group
            message = json.dumps(payload)
            print(f"[DEBUG] Message content: {message}")
            self.connection.send("SendMessage", [group, target, message])
            print(f"[DEBUG] Message sent successfully to {device_target.device_id}")
            
            return True
            
        except Exception as e:
            print(f"[DEBUG] ERROR in send_to_device: {e}")
            import traceback
            print(f"[DEBUG] send_to_device traceback: {traceback.format_exc()}")
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
        print(f"[DEBUG] send_to_devices START: {event.trace_id}, devices: {event.target_devices}")
        self._increment_processed()
        device_targets = []
        for device_id in event.target_devices:
            transport_config = TransportConfig(
                type=TransportType.SIGNALR,
                config={'group': device_id, 'target': 'ingress'}
            )
            device_target = DeviceTarget(device_id=device_id, transport_config=transport_config, object=event.object, value=event.value)
            device_targets.append(device_target)
        
        print(f"[DEBUG] Prepared {len(device_targets)} device targets")
        success_count = 0
        for i, device_target in enumerate(device_targets):
            print(f"[DEBUG] Processing device {i+1}/{len(device_targets)}: {device_target.device_id}")
            try:
                success = await self.transport.send_to_device(device_target)
                print(f"[DEBUG] Device {device_target.device_id} send result: {success}")
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
                    print(f"[DEBUG] Failed to deliver to device: {device_target.device_id}")
                    self.logger.warning("TRANSPORTS LAYER: Failed to deliver to device", 
                                      trace_id=event.trace_id,
                                      device_id=device_target.device_id)
                    
            except Exception as e:
                print(f"[DEBUG] ERROR delivering to device {device_target.device_id}: {e}")
                import traceback
                print(f"[DEBUG] send_to_devices error traceback: {traceback.format_exc()}")
                self.logger.error("TRANSPORTS LAYER: Error delivering to device",
                                trace_id=event.trace_id,
                                device_id=device_target.device_id,
                                error=str(e))
        
        print(f"[DEBUG] send_to_devices COMPLETED: {success_count}/{len(device_targets)} successful")
        return LayerResult(success=success_count > 0, processed_count=len(device_targets), error_count=len(device_targets) - success_count, data=device_targets)