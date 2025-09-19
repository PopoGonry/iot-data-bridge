#!/usr/bin/env python3
"""
IoT Data Bridge - MQTT Main Entry Point
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

import structlog
import yaml

from layers.input_mqtt import InputLayer
from layers.mapping import MappingLayer
from layers.resolver import ResolverLayer
from layers.transports_mqtt import TransportsLayer
from layers.logging import LoggingLayer
from catalogs.mapping_catalog import MappingCatalog
from catalogs.device_catalog import DeviceCatalog
from models.config import AppConfig
from models.events import IngressEvent, MappedEvent, ResolvedEvent, MiddlewareEventLog, DeviceIngestLog


class IoTDataBridge:
    """Main IoT Data Bridge application - MQTT only"""
    
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
            
            self.logger.info("IoT Data Bridge (MQTT) initialized successfully")
            
        except Exception as e:
            print(f"Failed to initialize IoT Data Bridge: {e}")
            sys.exit(1)
    
    async def _load_config(self):
        """Load configuration from YAML file"""
        if self.config_path:
            # Use specified config file
            config_file = Path(self.config_path)
            if not config_file.exists():
                raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        else:
            # Use default config file
            config_file = Path("config/app-mqtt.yaml")
            if not config_file.exists():
                raise FileNotFoundError(f"Configuration file not found: {config_file}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        self.config = AppConfig(**config_data)
        print(f"Loaded configuration from: {config_file}")
    
    def _setup_logging(self):
        """Setup structured logging"""
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
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
            self._on_ingress_event
        )
        
        # Initialize mapping layer
        self.mapping_layer = MappingLayer(
            self.mapping_catalog,
            self._on_mapped_event
        )
        
        # Initialize resolver layer
        self.resolver_layer = ResolverLayer(
            self.device_catalog,
            self._on_resolved_event
        )
        
        # Initialize transports layer
        self.transports_layer = TransportsLayer(
            self.config.transports,
            self.device_catalog
        )
        
        # Initialize logging layer
        self.logging_layer = LoggingLayer(
            self.config.logging
        )
        
        self.logger.info("Layers initialized successfully")
    
    async def _on_ingress_event(self, event: IngressEvent):
        """Handle ingress event"""
        try:
            # Process through mapping layer
            await self.mapping_layer.process_event(event)
        except Exception as e:
            self.logger.error("Error processing ingress event", 
                            event_uuid=event.uuid, 
                            error=str(e))
    
    async def _on_mapped_event(self, event: MappedEvent):
        """Handle mapped event"""
        try:
            # Process through resolver layer
            await self.resolver_layer.process_event(event)
        except Exception as e:
            self.logger.error("Error processing mapped event", 
                            event_uuid=event.uuid, 
                            error=str(e))
    
    async def _on_resolved_event(self, event: ResolvedEvent):
        """Handle resolved event"""
        try:
            # Process through transports layer
            transport_events = await self.transports_layer.send_event(event)
            
            # Log all events
            for transport_event in transport_events:
                await self.logging_layer.log_transport_event(transport_event)
            
        except Exception as e:
            self.logger.error("Error processing resolved event", 
                            event_uuid=event.uuid, 
                            error=str(e))
    
    async def start(self):
        """Start the IoT Data Bridge"""
        try:
            self.is_running = True
            self.logger.info("Starting IoT Data Bridge (MQTT)")
            
            # Start input layer
            await self.input_layer.start()
            
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
        
        if self.input_layer:
            await self.input_layer.stop()
        
        self.logger.info("IoT Data Bridge (MQTT) stopped")


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
