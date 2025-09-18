#!/usr/bin/env python3
"""
IoT Data Bridge - MQTT Only Main Entry Point
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

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
    """Main IoT Data Bridge application - MQTT Only"""
    
    def __init__(self, config_path: str = "config/app-mqtt.yaml"):
        self.config_path = config_path
        self.config = None
        self.logger = None
        self.running = False
        
        # Layers
        self.input_layer = None
        self.mapping_layer = None
        self.resolver_layer = None
        self.transports_layer = None
        self.logging_layer = None
        
        # Catalogs
        self.mapping_catalog = None
        self.device_catalog = None
        
    async def initialize(self):
        """Initialize the application"""
        try:
            # Load configuration
            await self._load_config()
            
            # Setup logging
            self._setup_logging()
            
            # Initialize catalogs
            await self._initialize_catalogs()
            
            # Initialize layers
            await self._initialize_layers()
            
            self.logger.info("IoT Data Bridge (MQTT Only) initialized successfully")
            
        except Exception as e:
            print(f"Failed to initialize IoT Data Bridge: {e}")
            sys.exit(1)
    
    async def _load_config(self):
        """Load configuration from YAML file"""
        config_file = Path(self.config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        self.config = AppConfig(**config_data)
    
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
        from logging.handlers import RotatingFileHandler
        
        # Create logs directory
        log_file = Path(self.config.logging.file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Setup rotating file handler
        file_handler = RotatingFileHandler(
            self.config.logging.file,
            encoding='utf-8',
            maxBytes=self.config.logging.max_size,
            backupCount=self.config.logging.backup_count
        )
        file_handler.setLevel(getattr(logging, self.config.logging.level.upper()))
        
        # Setup console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, self.config.logging.level.upper()))
        
        # Setup formatter
        formatter = logging.Formatter('%(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Configure logging
        logging.basicConfig(
            level=getattr(logging, self.config.logging.level.upper()),
            format='%(message)s',
            handlers=[file_handler, console_handler]
        )
        
        self.logger = structlog.get_logger("iot_data_bridge_mqtt")
    
    async def _initialize_catalogs(self):
        """Initialize mapping and device catalogs"""
        self.mapping_catalog = MappingCatalog(self.config.mapping_catalog_path)
        await self.mapping_catalog.load()
        
        self.device_catalog = DeviceCatalog(self.config.device_catalog_path)
        await self.device_catalog.load()
    
    async def _initialize_layers(self):
        """Initialize all layers"""
        # Initialize logging layer first
        self.logging_layer = LoggingLayer(self.config.logging)
        
        # Initialize transports layer
        self.transports_layer = TransportsLayer(
            self.config.transports,
            self.device_catalog,
            self._log_device_ingest
        )
        
        # Initialize resolver layer
        self.resolver_layer = ResolverLayer(
            self.device_catalog,
            self._log_middleware_event
        )
        
        # Set resolver -> transports callback
        self.resolver_layer.set_transports_callback(self._handle_resolved_event)
        
        # Initialize mapping layer
        self.mapping_layer = MappingLayer(
            self.mapping_catalog,
            self._handle_mapped_event
        )
        
        # Initialize input layer (MQTT only)
        self.input_layer = InputLayer(
            self.config.input,
            self._handle_ingress_event
        )
    
    async def _handle_ingress_event(self, event: IngressEvent):
        """Handle ingress event from input layer"""
        await self.mapping_layer.map_event(event)
    
    async def _handle_mapped_event(self, event: MappedEvent):
        """Handle mapped event from mapping layer"""
        await self.resolver_layer.resolve_event(event)
    
    async def _handle_resolved_event(self, event: ResolvedEvent):
        """Handle resolved event from resolver layer"""
        await self.transports_layer.send_to_devices(event)
    
    async def _log_middleware_event(self, event: MiddlewareEventLog):
        """Log middleware event"""
        await self.logging_layer.log_middleware_event(event)
    
    async def _log_device_ingest(self, event: DeviceIngestLog):
        """Log device ingest event"""
        await self.logging_layer.log_device_ingest(event)
    
    async def start(self):
        """Start the application"""
        self.running = True
        self.logger.info("Starting IoT Data Bridge (MQTT Only)")
        
        try:
            # Start all layers
            await asyncio.gather(
                self.input_layer.start(),
                self.transports_layer.start(),
                self.logging_layer.start(),
                return_exceptions=True
            )
            
            # Keep running until stopped
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            self.logger.error("Error in main loop", error=str(e))
            raise
    
    async def stop(self):
        """Stop the application"""
        self.running = False
        self.logger.info("Stopping IoT Data Bridge (MQTT Only)")
        
        # Stop all layers
        if self.input_layer:
            await self.input_layer.stop()
        if self.transports_layer:
            await self.transports_layer.stop()
        if self.logging_layer:
            await self.logging_layer.stop()
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating shutdown")
            asyncio.create_task(self.stop())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


async def main():
    """Main entry point"""
    app = IoTDataBridge()
    
    try:
        await app.initialize()
        app.setup_signal_handlers()
        await app.start()
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
    except Exception as e:
        print(f"Application error: {e}")
        sys.exit(1)
    finally:
        await app.stop()


if __name__ == "__main__":
    asyncio.run(main())
