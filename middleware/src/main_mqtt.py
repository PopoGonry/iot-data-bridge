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
            
            # Start MQTT broker
            self._start_mqtt_broker()
            
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
        # Custom formatter for detailed logs
        def detailed_formatter(logger, method_name, event_dict):
            """Detailed formatter showing all fields"""
            message = event_dict.get('event', '')
            
            # Extract key fields
            trace_id = event_dict.get('trace_id', '')
            equip_tag = event_dict.get('equip_tag', '')
            message_id = event_dict.get('message_id', '')
            raw_value = event_dict.get('raw_value', '')
            object_name = event_dict.get('object', '')
            value = event_dict.get('value', '')
            value_type = event_dict.get('value_type', '')
            device_id = event_dict.get('device_id', '')
            target_devices = event_dict.get('target_devices', '')
            device_count = event_dict.get('device_count', '')
            total_devices = event_dict.get('total_devices', '')
            success_count = event_dict.get('success_count', '')
            failed_count = event_dict.get('failed_count', '')
            topic = event_dict.get('topic', '')
            source = event_dict.get('source', '')
            
            # Build detailed message
            parts = [message]
            
            if trace_id:
                parts.append(f"trace_id={trace_id}")
            if equip_tag:
                parts.append(f"equip_tag={equip_tag}")
            if message_id:
                parts.append(f"message_id={message_id}")
            if raw_value != '':
                parts.append(f"raw_value={raw_value}")
            if object_name:
                parts.append(f"object={object_name}")
            if value != '':
                parts.append(f"value={value}")
            if value_type:
                parts.append(f"value_type={value_type}")
            if device_id:
                parts.append(f"device_id={device_id}")
            if target_devices:
                parts.append(f"target_devices={target_devices}")
            if device_count:
                parts.append(f"device_count={device_count}")
            if total_devices:
                parts.append(f"total_devices={total_devices}")
            if success_count:
                parts.append(f"success_count={success_count}")
            if failed_count:
                parts.append(f"failed_count={failed_count}")
            if topic:
                parts.append(f"topic={topic}")
            if source:
                parts.append(f"source={source}")
            
            return " ".join(parts)
        
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_log_level,
                structlog.processors.TimeStamper(fmt="%H:%M:%S"),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                detailed_formatter
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
        file_handler.setLevel(logging.INFO)  # 파일에는 INFO 레벨만
        
        # Setup console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)  # 콘솔에는 모든 로그 표시
        
        # Setup formatters (Device와 동일한 포맷)
        file_formatter = logging.Formatter(
            '%(asctime)s | INFO | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-5s | %(message)s',
            datefmt='%H:%M:%S'
        )
        
        file_handler.setFormatter(file_formatter)
        console_handler.setFormatter(console_formatter)
        
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
        # Extract raw data for logging
        raw_payload = event.raw.get('payload', {})
        equip_tag = raw_payload.get('Equip.Tag', 'Unknown')
        message_id = raw_payload.get('Message.ID', 'Unknown')
        raw_value = raw_payload.get('VALUE', 'Unknown')
        
        self.logger.info("INPUT LAYER: Raw data received", 
                        trace_id=event.trace_id, 
                        equip_tag=equip_tag,
                        message_id=message_id,
                        raw_value=raw_value,
                        source=event.meta.get('source', 'unknown'))
        await self.mapping_layer.map_event(event)
    
    async def _handle_mapped_event(self, event: MappedEvent):
        """Handle mapped event from mapping layer"""
        self.logger.info("MAPPING LAYER: Data parsed and mapped", 
                        trace_id=event.trace_id, 
                        object=event.object, 
                        value=event.value, 
                        value_type=event.value_type.value)
        await self.resolver_layer.resolve_event(event)
    
    async def _handle_resolved_event(self, event: ResolvedEvent):
        """Handle resolved event from resolver layer"""
        self.logger.info("RESOLVER LAYER: Target devices identified", 
                        trace_id=event.trace_id, 
                        object=event.object, 
                        target_devices=event.target_devices,
                        device_count=len(event.target_devices))
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
        
        # Stop all layers
        if self.input_layer:
            await self.input_layer.stop()
        if self.transports_layer:
            await self.transports_layer.stop()
        if self.logging_layer:
            await self.logging_layer.stop()
        
        # Stop MQTT broker
        self._stop_mqtt_broker()
    
    def _start_mqtt_broker(self):
        """Start MQTT broker"""
        import subprocess
        import os
        
        try:
            # Stop any existing mosquitto processes (silently ignore errors)
            try:
                subprocess.run(["pkill", "mosquitto"], check=False, capture_output=True)
            except:
                pass
            
            # Get the directory where mosquitto.conf is located
            # Try multiple possible locations
            possible_paths = [
                Path(self.config_path).parent / "mosquitto.conf",  # config/mosquitto.conf
                Path("mosquitto.conf"),  # current directory
                Path("../mosquitto.conf"),  # parent directory
            ]
            
            mosquitto_conf = None
            for path in possible_paths:
                if path.exists():
                    mosquitto_conf = path
                    break
            
            if not mosquitto_conf:
                print(f"Warning: mosquitto.conf not found. Searched: {[str(p) for p in possible_paths]}")
                return
            
            # Start mosquitto with the config file
            result = subprocess.run([
                "mosquitto", 
                "-c", str(mosquitto_conf), 
                "-d"
            ], cwd=str(mosquitto_conf.parent), capture_output=True, text=True)
            
            if result.returncode == 0:
                print("MQTT broker started successfully")
            else:
                print(f"Failed to start MQTT broker: {result.stderr}")
                
        except FileNotFoundError:
            print("Warning: mosquitto not found. Please install mosquitto or start MQTT broker manually.")
        except Exception as e:
            print(f"Error starting MQTT broker: {e}")
    
    def _stop_mqtt_broker(self):
        """Stop MQTT broker"""
        import subprocess
        try:
            subprocess.run(["pkill", "mosquitto"], check=False, capture_output=True)
        except Exception as e:
            pass
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
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