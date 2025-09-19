#!/usr/bin/env python3
"""
IoT Data Bridge - SignalR Main Entry Point
"""

import asyncio
import logging
import signal
import sys
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
            
            self.logger.info("IoT Data Bridge (SignalR) initialized successfully")
            
        except Exception as e:
            print(f"Failed to initialize IoT Data Bridge: {e}")
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
        print(f"Loaded configuration from: {config_file}")
    
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
        
        self.logger.info("Catalogs initialized successfully")
    
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
        
        # Initialize resolver layer
        self.resolver_layer = ResolverLayer(
            self.device_catalog,
            self._handle_resolved_event
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
        
        self.logger.info("Layers initialized successfully")
    
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
            
            # Start SignalR hub
            result = subprocess.run([
                "dotnet", "run"
            ], cwd=str(signalr_hub_dir), capture_output=True, text=True)
            
            if result.returncode == 0:
                print("SignalR hub started successfully")
            else:
                print(f"Failed to start SignalR hub: {result.stderr}")
                
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
        # No console log - only file log
        await self.mapping_layer.map_event(event)
    
    async def _handle_mapped_event(self, event: MappedEvent):
        """Handle mapped event from mapping layer"""
        # No console log - only file log
        await self.resolver_layer.resolve_event(event)
    
    async def _handle_resolved_event(self, event: ResolvedEvent):
        """Handle resolved event from resolver layer"""
        # No console log - only file log
        await self.transports_layer.send_to_devices(event)
    
    async def _handle_device_ingest(self, event: DeviceIngestLog):
        """Handle device ingest log"""
        await self.logging_layer.log_device_ingest(event)
    
    async def start(self):
        """Start the IoT Data Bridge"""
        try:
            self.is_running = True
            self.logger.info("Starting IoT Data Bridge (SignalR)")
            
            # Start all layers
            self.logger.info("Starting input layer...")
            await self.input_layer.start()
            self.logger.info("Input layer started")
            
            self.logger.info("Starting mapping layer...")
            await self.mapping_layer.start()
            self.logger.info("Mapping layer started")
            
            self.logger.info("Starting resolver layer...")
            await self.resolver_layer.start()
            self.logger.info("Resolver layer started")
            
            self.logger.info("Starting transports layer...")
            await self.transports_layer.start()
            self.logger.info("Transports layer started")
            
            self.logger.info("Starting logging layer...")
            await self.logging_layer.start()
            self.logger.info("Logging layer started")
            
            self.logger.info("All layers started successfully")
            
            # Keep running
            while self.is_running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            self.logger.info("Received shutdown signal")
        except Exception as e:
            self.logger.error("Error in main loop", error=str(e))
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the IoT Data Bridge"""
        self.is_running = False
        
        # Stop all layers
        if self.input_layer:
            await self.input_layer.stop()
        if self.mapping_layer:
            await self.mapping_layer.stop()
        if self.resolver_layer:
            await self.resolver_layer.stop()
        if self.transports_layer:
            await self.transports_layer.stop()
        if self.logging_layer:
            await self.logging_layer.stop()
        
        # Stop SignalR hub
        self._stop_signalr_hub()
        
        self.logger.info("IoT Data Bridge (SignalR) stopped")


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
        asyncio.create_task(bridge.stop())
    
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