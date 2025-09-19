#!/usr/bin/env python3
"""
IoT Device - Simulates a device receiving data from middleware
"""

import asyncio
import json
import sys
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import structlog
from aiomqtt import Client


class IoTDevice:
    """IoT Device that receives data from middleware"""
    
    def __init__(self, device_id: str, config: Dict[str, Any]):
        self.device_id = device_id
        self.config = config
        self.client = None
        self.is_running = False
        self.data_count = 0
        self.logger = structlog.get_logger(f"device_{device_id}")
    
    async def start(self):
        """Start the device"""
        # Get MQTT settings
        mqtt_config = self.config.get('mqtt', {})
        host = mqtt_config.get('host', 'localhost')
        port = mqtt_config.get('port', 1883)
        topic = mqtt_config.get('topic', f'devices/{self.device_id.lower()}/ingress')
        qos = mqtt_config.get('qos', 1)
        
        self.logger.info("Starting device", 
                       device_id=self.device_id,
                       host=host,
                       port=port,
                       topic=topic)
        
        # Create MQTT client
        self.client = Client(
            hostname=host,
            port=port,
            username=mqtt_config.get('username'),
            password=mqtt_config.get('password'),
            keepalive=mqtt_config.get('keepalive', 60)
        )
        
        try:
            async with self.client:
                self.logger.debug("MQTT broker connection successful", host=host, port=port)
                
                self.logger.debug("Starting MQTT topic subscription", topic=topic, qos=qos)
                await self.client.subscribe(topic, qos=qos)
                self.logger.debug("MQTT topic subscription completed", topic=topic)
                
                self.is_running = True
                self.logger.info("Device waiting for messages")
                
                # Listen for messages
                async for message in self.client.messages:
                    if not self.is_running:
                        break
                    
                    try:
                        self.logger.debug("Raw MQTT message received", 
                                       topic=message.topic,
                                       payload_size=len(message.payload),
                                       qos=message.qos)
                        await self._handle_message(message)
                    except Exception as e:
                        self.logger.error("Error handling message", error=str(e))
                        
        except Exception as e:
            self.logger.error("Device connection failed", 
                            error=str(e), 
                            error_type=type(e).__name__,
                            host=host, 
                            port=port)
            raise
    
    async def stop(self):
        """Stop the device"""
        self.logger.info("Stopping device", device_id=self.device_id)
        self.is_running = False
        # aiomqtt client will be closed when exiting the async with context
    
    async def _handle_message(self, message):
        """Handle incoming MQTT message"""
        try:
            # Parse message payload
            payload = json.loads(message.payload.decode('utf-8'))
            
            # Extract data
            object_name = payload.get('object')
            value = payload.get('value')
            
            if not all([object_name, value is not None]):
                self.logger.warning("Invalid message format", payload=payload)
                return
            
            # Increment counter
            self.data_count += 1
            
            # Log received data
            self.logger.info("Data received",
                           device_id=self.device_id,
                           object=object_name,
                           value=value,
                           count=self.data_count)
            
        except json.JSONDecodeError as e:
            self.logger.error("Invalid JSON in message", error=str(e))
        except Exception as e:
            self.logger.error("Error processing message", error=str(e))


async def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python device.py <device_id> [mqtt_host] [mqtt_port]")
        sys.exit(1)
    
    device_id = sys.argv[1]
    mqtt_host = sys.argv[2] if len(sys.argv) > 2 else "localhost"
    mqtt_port = int(sys.argv[3]) if len(sys.argv) > 3 else 1883
    
    print(f"Starting IoT Device: {device_id}")
    print(f"MQTT Host: {mqtt_host}:{mqtt_port}")
    
    # Load configuration from template or create default
    config_file = Path("device_config.yaml")
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        print(f"Loaded configuration from: {config_file}")
    else:
        # Create default configuration
        config_data = {
            'device_id': device_id,
            'mqtt': {
                'host': mqtt_host,
                'port': mqtt_port,
                'topic': f'devices/{device_id.lower()}/ingress',
                'qos': 1,
                'keepalive': 60,
                'username': None,
                'password': None
            },
            'logging': {
                'level': 'INFO',
                'file': 'device.log',
                'max_size': 10485760,
                'backup_count': 5
            }
        }
        print("Using default configuration")
    
    # Override device_id and MQTT settings from command line
    config_data['device_id'] = device_id
    config_data['mqtt']['host'] = mqtt_host
    config_data['mqtt']['port'] = mqtt_port
    config_data['mqtt']['topic'] = f'devices/{device_id.lower()}/ingress'
    
    config = config_data
    
    print(f"Device {device_id} configuration:")
    print(f"  - MQTT Host: {config['mqtt']['host']}:{config['mqtt']['port']}")
    print(f"  - Topic: {config['mqtt']['topic']}")
    
    # Setup logging
    import logging
    from logging.handlers import RotatingFileHandler
    
    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Setup file handler
    log_file = logs_dir / config.get('logging', {}).get('file', 'device.log')
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=config.get('logging', {}).get('max_size', 10485760),  # 10MB
        backupCount=config.get('logging', {}).get('backup_count', 5),
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    
    # Setup console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)  # 콘솔에는 모든 로그 표시
    
    # Setup formatters
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
        level=logging.INFO,
        handlers=[file_handler, console_handler],
        force=True
    )
    
    # Configure structlog with custom formatter
    def simple_formatter(logger, method_name, event_dict):
        """Simple formatter for clean logs"""
        level = event_dict.get('level', 'INFO').upper()
        message = event_dict.get('event', '')
        
        # Extract key fields
        device_id = event_dict.get('device_id', '')
        object_name = event_dict.get('object', '')
        value = event_dict.get('value', '')
        
        if object_name and value:
            return f"{message} device_id={device_id} object={object_name} value={value}"
        elif device_id:
            return f"{message} device_id={device_id}"
        else:
            return message
    
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="%H:%M:%S"),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            simple_formatter
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Create and start device
    print(f"Creating device instance for {device_id}...")
    device = IoTDevice(device_id, config)
    
    try:
        print(f"Starting device {device_id}...")
        await device.start()
    except KeyboardInterrupt:
        print(f"\nShutting down {device_id} Device...")
    except Exception as e:
        print(f"Error starting device: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await device.stop()


if __name__ == "__main__":
    asyncio.run(main())