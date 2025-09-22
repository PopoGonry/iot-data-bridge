#!/usr/bin/env python3
"""
IoT Data Bridge - SignalR Main Entry Point
"""

import asyncio
import logging
import signal
import sys
import time
from pathlib import Path

import structlog
import yaml

from layers.input_signalr import InputLayer
from layers.mapping import MappingLayer
from layers.resolver import ResolverLayer
from layers.transports_signalr import TransportsLayer
from layers.logging import LoggingLayer
from catalogs.mapping_catalog import MappingCatalog
from catalogs.device_catalog import DeviceCatalog
from models.config import AppConfig
from models.events import IngressEvent, MappedEvent, ResolvedEvent, MiddlewareEventLog, DeviceIngestLog


class IoTDataBridge:
    """Main IoT Data Bridge application - SignalR only"""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path
        self.config = None
        self.logger = None
        
        # Layer instances
        self.mapping_catalog = None
        self.device_catalog = None
        self.input_layer = None
        self.mapping_layer = None
        self.resolver_layer = None
        self.transports_layer = None
        self.logging_layer = None
        
        # Running state
        self.is_running = False
    
    async def initialize(self):
        """Initialize the IoT Data Bridge"""
        try:
            # Load configuration
            await self._load_config()
            
            # Setup logging
            self._setup_logging()
            
            # Initialize catalogs
            await self._initialize_catalogs()
            
            # Initialize layers
            await self._initialize_layers()
            
            # Start SignalR hub
            self._start_signalr_hub()
            
        except Exception as e:
            print(f"Failed to initialize IoT Data Bridge: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    async def _load_config(self):
        """Load configuration from YAML file"""
        if self.config_path:
            config_file = Path(self.config_path)
            if not config_file.exists():
                raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        else:
            # Try multiple possible config file locations
            config_files = [
                "config/app-signalr.yaml",
                "middleware/config/app-signalr.yaml",
                "app-signalr.yaml"
            ]
            
            config_file = None
            for file in config_files:
                if Path(file).exists():
                    config_file = Path(file)
                    break
            
            if not config_file:
                raise FileNotFoundError(f"No configuration file found. Available options: {config_files}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        self.config = AppConfig(**config_data)
    
    def _setup_logging(self):
        """Setup structured logging"""
        # Custom formatter for console logs (same as file format)
        def console_formatter(logger, method_name, event_dict):
            """Console formatter matching file log format"""
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message = event_dict.get('event', '')
            
            # Extract key fields
            device_id = event_dict.get('device_id', '')
            object_name = event_dict.get('object', '')
            value = event_dict.get('value', '')
            
            # Show Data sent logs in console with proper format (no timestamp - structlog will add it)
            if message == "Data sent" and device_id and object_name and value != '':
                return f"Data sent | device_id={device_id} | object={object_name} | value={value}"
            else:
                # Show other important logs normally
                return message
        
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_log_level,
                structlog.processors.TimeStamper(fmt="%H:%M:%S"),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                console_formatter # Use the custom console formatter
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
        
        # Setup file logging
        log_file = Path(self.config.logging.file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=getattr(logging, self.config.logging.level.upper()),
            format='%(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        self.logger = structlog.get_logger("iot_data_bridge")
    
    async def _initialize_catalogs(self):
        """Initialize mapping and device catalogs"""
        # Initialize mapping catalog
        mapping_catalog_path = Path(self.config.mapping_catalog_path)
        if not mapping_catalog_path.exists():
            raise FileNotFoundError(f"Mapping catalog not found: {mapping_catalog_path}")
        
        self.mapping_catalog = MappingCatalog(mapping_catalog_path)
        await self.mapping_catalog.load()
        
        # Initialize device catalog
        device_catalog_path = Path(self.config.device_catalog_path)
        if not device_catalog_path.exists():
            raise FileNotFoundError(f"Device catalog not found: {device_catalog_path}")
        
        self.device_catalog = DeviceCatalog(device_catalog_path)
        await self.device_catalog.load()
    
    async def _initialize_layers(self):
        """Initialize all layers"""
        # Initialize input layer
        self.input_layer = InputLayer(
            self.config.input,
            self._handle_ingress_event
        )
        
        # Initialize mapping layer
        self.mapping_layer = MappingLayer(
            self.mapping_catalog,
            self._handle_mapped_event
        )
        
        # Initialize resolver layer (로깅 콜백 없음)
        self.resolver_layer = ResolverLayer(
            self.device_catalog,
            None  # 로깅 콜백 비활성화
        )
        
        # Initialize transports layer
        self.transports_layer = TransportsLayer(
            self.config.transports,
            self.device_catalog,
            self._handle_device_ingest
        )
        
        # Initialize logging layer
        self.logging_layer = LoggingLayer(
            self.config.logging
        )
        
        # Set up layer callbacks (올바른 콜백 설정)
        self.resolver_layer.set_transports_callback(self._handle_resolved_event)
    
    def _start_signalr_hub(self):
        """Start SignalR hub"""
        import subprocess
        import os
        
        try:
            # Stop any existing dotnet processes (silently ignore errors)
            try:
                subprocess.run(["pkill", "dotnet"], check=False, capture_output=True)
            except:
                pass
            
            # Get the directory where signalr_hub is located
            possible_paths = [
                Path("signalr_hub"),  # current directory
                Path("../signalr_hub"),  # parent directory
                Path("middleware/signalr_hub"),  # middleware subdirectory
            ]
            
            signalr_hub_dir = None
            for path in possible_paths:
                if path.exists():
                    signalr_hub_dir = path
                    break
            
            if not signalr_hub_dir:
                print(f"Warning: signalr_hub directory not found. Searched: {[str(p) for p in possible_paths]}")
                return
            
            # Start SignalR hub in background
            result = subprocess.Popen([
                "dotnet", "run"
            ], cwd=str(signalr_hub_dir), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Give it a moment to start
            import time
            time.sleep(2)
            
            # Check if process is still running
            if result.poll() is None:
                pass  # SignalR hub started successfully
            else:
                stdout, stderr = result.communicate()
                print(f"Failed to start SignalR hub: {stderr.decode()}")
                
        except FileNotFoundError:
            print("Warning: dotnet not found. Please install .NET SDK or start SignalR hub manually.")
        except Exception as e:
            print(f"Error starting SignalR hub: {e}")
    
    def _stop_signalr_hub(self):
        """Stop SignalR hub"""
        import subprocess
        try:
            subprocess.run(["pkill", "dotnet"], check=False, capture_output=True)
        except Exception as e:
            pass
    
        async def _handle_ingress_event(self, event: IngressEvent):
            """Handle ingress event from input layer"""
            print(f"[DEBUG] _handle_ingress_event START: {event.trace_id}")
            print(f"[DEBUG] Ingress event raw data: {event.raw}")
            print(f"[DEBUG] Ingress event meta: {event.meta}")
            try:
                print(f"[DEBUG] Calling mapping_layer.map_event for: {event.trace_id}")
                await self.mapping_layer.map_event(event)
                print(f"[DEBUG] _handle_ingress_event COMPLETED: {event.trace_id}")
            except Exception as e:
                print(f"[DEBUG] ERROR in _handle_ingress_event: {e}")
                import traceback
                print(f"[DEBUG] _handle_ingress_event traceback: {traceback.format_exc()}")
                raise
    
        async def _handle_mapped_event(self, event: MappedEvent):
            """Handle mapped event from mapping layer"""
            print(f"[DEBUG] _handle_mapped_event START: {event.trace_id}")
            print(f"[DEBUG] Mapped event object: {event.object}")
            print(f"[DEBUG] Mapped event value: {event.value}")
            print(f"[DEBUG] Mapped event device_id: {event.device_id}")
            try:
                print(f"[DEBUG] Calling resolver_layer.resolve_event for: {event.trace_id}")
                await self.resolver_layer.resolve_event(event)
                print(f"[DEBUG] _handle_mapped_event COMPLETED: {event.trace_id}")
            except Exception as e:
                print(f"[DEBUG] ERROR in _handle_mapped_event: {e}")
                import traceback
                print(f"[DEBUG] _handle_mapped_event traceback: {traceback.format_exc()}")
                raise
    
        async def _handle_resolved_event(self, event: ResolvedEvent):
            """Handle resolved event from resolver layer"""
            print(f"[DEBUG] _handle_resolved_event START: {event.trace_id}")
            print(f"[DEBUG] Resolved event target_devices: {event.target_devices}")
            print(f"[DEBUG] Resolved event object: {event.object}")
            print(f"[DEBUG] Resolved event value: {event.value}")
            try:
                print(f"[DEBUG] Calling transports_layer.send_to_devices for: {event.trace_id}")
                await self.transports_layer.send_to_devices(event)
                print(f"[DEBUG] _handle_resolved_event COMPLETED: {event.trace_id}")
            except Exception as e:
                print(f"[DEBUG] ERROR in _handle_resolved_event: {e}")
                import traceback
                print(f"[DEBUG] _handle_resolved_event traceback: {traceback.format_exc()}")
                raise
    
    async def _handle_device_ingest(self, event: DeviceIngestLog):
        """Handle device ingest log"""
        await self.logging_layer.log_device_ingest(event)
    
    async def start(self):
        """Start the IoT Data Bridge"""
        try:
            self.is_running = True
            
            # Start all layers
            await self.input_layer.start()
            await self.mapping_layer.start()
            await self.resolver_layer.start()
            await self.transports_layer.start()
            await self.logging_layer.start()
            
            print("IoT Data Bridge started successfully!")
            print("Press Ctrl+C to stop")
            
            # Keep running with timeout
            loop_count = 0
            while self.is_running:
                loop_count += 1
                if loop_count % 10 == 0:  # Every 10 seconds
                    print(f"[DEBUG] Main loop running... count: {loop_count}")
                    # Check layer states
                    print(f"[DEBUG] Layer states - Input: {getattr(self.input_layer, 'is_running', 'N/A')}, "
                          f"Mapping: {getattr(self.mapping_layer, 'is_running', 'N/A')}, "
                          f"Resolver: {getattr(self.resolver_layer, 'is_running', 'N/A')}, "
                          f"Transports: {getattr(self.transports_layer, 'is_running', 'N/A')}")
                    
                    # Check SignalR connection status
                    if hasattr(self.input_layer, 'handler') and self.input_layer.handler:
                        handler = self.input_layer.handler
                        last_msg_time = getattr(handler, 'last_message_time', 0)
                        current_time = time.time()
                        time_since_last_msg = current_time - last_msg_time if last_msg_time > 0 else 0
                        print(f"[DEBUG] SignalR last message: {time_since_last_msg:.1f}s ago")
                        
                        # Check if SignalR connection is still active
                        if hasattr(handler, 'connection') and handler.connection:
                            try:
                                # Try to check connection status
                                if hasattr(handler.connection, 'transport') and hasattr(handler.connection.transport, '_ws'):
                                    if handler.connection.transport._ws and handler.connection.transport._ws.sock:
                                        print(f"[DEBUG] SignalR connection: ACTIVE")
                                        # Check if connection is actually receiving data
                                        if time_since_last_msg > 30:  # More than 30 seconds without data
                                            print(f"[DEBUG] WARNING: No data received for {time_since_last_msg:.1f}s - connection may be stuck")
                                            # Try to trigger reconnection
                                            if hasattr(handler, '_attempt_reconnection'):
                                                print(f"[DEBUG] Attempting to reconnect SignalR input connection...")
                                                try:
                                                    # Schedule reconnection in the event loop
                                                    asyncio.create_task(handler._attempt_reconnection())
                                                except Exception as e:
                                                    print(f"[DEBUG] Failed to schedule reconnection: {e}")
                                    else:
                                        print(f"[DEBUG] SignalR connection: INACTIVE - WebSocket closed")
                                else:
                                    print(f"[DEBUG] SignalR connection: UNKNOWN state")
                            except Exception as e:
                                print(f"[DEBUG] SignalR connection check error: {e}")
                        else:
                            print(f"[DEBUG] SignalR connection: NOT INITIALIZED")
                
                try:
                    await asyncio.wait_for(asyncio.sleep(1), timeout=1.0)
                except asyncio.TimeoutError:
                    print(f"[DEBUG] Main loop timeout at count {loop_count}")
                    continue
                except Exception as e:
                    print(f"[DEBUG] Error in main loop at count {loop_count}: {e}")
                    import traceback
                    print(f"[DEBUG] Main loop traceback: {traceback.format_exc()}")
                    break
                
        except KeyboardInterrupt:
            print("\nKeyboard interrupt received")
        except Exception as e:
            print(f"Error in main loop: {e}")
        finally:
            print("Stopping IoT Data Bridge...")
            await self.stop()
    
    async def stop(self):
        """Stop the IoT Data Bridge"""
        self.is_running = False
        
        print("Stopping all layers...")
        
        # Stop all layers with timeout
        try:
            if self.input_layer:
                await asyncio.wait_for(self.input_layer.stop(), timeout=5.0)
        except Exception as e:
            print(f"Error stopping input layer: {e}")
        
        try:
            if self.mapping_layer:
                await asyncio.wait_for(self.mapping_layer.stop(), timeout=5.0)
        except Exception as e:
            print(f"Error stopping mapping layer: {e}")
        
        try:
            if self.resolver_layer:
                await asyncio.wait_for(self.resolver_layer.stop(), timeout=5.0)
        except Exception as e:
            print(f"Error stopping resolver layer: {e}")
        
        try:
            if self.transports_layer:
                await asyncio.wait_for(self.transports_layer.stop(), timeout=5.0)
        except Exception as e:
            print(f"Error stopping transports layer: {e}")
        
        try:
            if self.logging_layer:
                await asyncio.wait_for(self.logging_layer.stop(), timeout=5.0)
        except Exception as e:
            print(f"Error stopping logging layer: {e}")
        
        # Stop SignalR hub
        try:
            self._stop_signalr_hub()
        except Exception as e:
            print(f"Error stopping SignalR hub: {e}")
        
        print("IoT Data Bridge stopped successfully!")


async def main():
    """Main entry point"""
    # Parse command line arguments
    config_path = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Create and initialize bridge
    bridge = IoTDataBridge(config_path)
    await bridge.initialize()
    
    # Setup signal handlers
    def signal_handler(signum, frame):
        print(f"\nReceived signal {signum}, shutting down...")
        bridge.is_running = False
        # Force stop all layers
        try:
            if bridge.input_layer:
                bridge.input_layer.is_running = False
            if bridge.transports_layer:
                bridge.transports_layer.is_running = False
        except:
            pass
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start the bridge
    await bridge.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)