#!/usr/bin/env python3
"""
IoT Device - Simple device that receives data via MQTT and logs it
"""

import asyncio
import json
import sys
import yaml
from pathlib import Path
from datetime import datetime
import structlog
from aiomqtt import Client


class IoTDevice:
    """Simple IoT Device that receives data and logs it"""
    
    def __init__(self, device_id: str, config: dict):
        self.device_id = device_id
        self.config = config
        self.logger = structlog.get_logger(f"device_{device_id}")
        self.is_running = False
        self.client = None
        self.data_count = 0
    
    async def start(self):
        """Start the device"""
        try:
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
            
            # Start MQTT client
            async with self.client:
                await self.client.subscribe(topic, qos=qos)
                self.logger.info("Subscribed to MQTT topic", topic=topic)
                
                self.is_running = True
                
                # Listen for messages
                async for message in self.client.messages:
                    if not self.is_running:
                        break
                    
                    try:
                        await self._handle_message(message)
                    except Exception as e:
                        self.logger.error("Error handling message", error=str(e))
                        
        except Exception as e:
            self.logger.error("Device error", error=str(e))
            raise
    
    async def stop(self):
        """Stop the device"""
        self.logger.info("Stopping device", device_id=self.device_id)
        self.is_running = False
        if self.client:
            await self.client.disconnect()
    
    async def _handle_message(self, message):
        """Handle incoming MQTT message"""
        try:
            # Parse message payload
            payload = json.loads(message.payload.decode('utf-8'))
            
            # Extract data
            object_name = payload.get('object')
            value = payload.get('value')
            timestamp = payload.get('timestamp')
            
            if not all([object_name, value is not None, timestamp]):
                self.logger.warning("Invalid message format", payload=payload)
                return
            
            # Increment counter
            self.data_count += 1
            
            # Log received data
            self.logger.info("Received data",
                           device_id=self.device_id,
                           object=object_name,
                           value=value,
                           timestamp=timestamp,
                           count=self.data_count)
            
        except json.JSONDecodeError as e:
            self.logger.error("Invalid JSON in message", error=str(e))
        except Exception as e:
            self.logger.error("Error processing message", error=str(e))


async def main():
    """Main function"""
    # Parse command line arguments
    if len(sys.argv) < 2:
        print("Usage: python device.py <device_id> [config_file]")
        print("       python device.py <device_id> [mqtt_host] [mqtt_port]")
        print("Example: python device.py VM-A")
        print("Example: python device.py VM-A device_config.yaml")
        print("Example: python device.py VM-A localhost 1883")
        sys.exit(1)
    
    device_id = sys.argv[1]
    
    # Check if second argument is a config file or mqtt_host
    if len(sys.argv) > 2 and sys.argv[2].endswith('.yaml'):
        # Load from config file
        config_path = sys.argv[2]
        config_file = Path(config_path)
        
        if not config_file.exists():
            print(f"Config file not found: {config_path}")
            sys.exit(1)
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        device_config = config_data
        print(f"Loaded configuration from {config_path}")
        
    else:
        # Use command line arguments
        mqtt_host = sys.argv[2] if len(sys.argv) > 2 else "localhost"
        mqtt_port = int(sys.argv[3]) if len(sys.argv) > 3 else 1883
        
        device_config = {
            'mqtt': {
                'host': mqtt_host,
                'port': mqtt_port,
                'topic': f'devices/{device_id.lower()}/ingress',
                'qos': 1,
                'keepalive': 60
            }
        }
        print(f"Using command line configuration")
    
    # Override device_id in config
    device_config['device_id'] = device_id
    
    # Ensure topic is set correctly
    if 'mqtt' not in device_config:
        device_config['mqtt'] = {}
    
    if 'topic' not in device_config['mqtt']:
        device_config['mqtt']['topic'] = f'devices/{device_id.lower()}/ingress'
    
    print(f"Device {device_id} configuration:")
    print(f"  - MQTT Host: {device_config['mqtt'].get('host', 'localhost')}:{device_config['mqtt'].get('port', 1883)}")
    print(f"  - Topic: {device_config['mqtt']['topic']}")
    
    # Setup logging
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
    
    # Create and start device
    device = IoTDevice(device_id, device_config)
    
    try:
        await device.start()
    except KeyboardInterrupt:
        print(f"\nShutting down {device_id} Device...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await device.stop()


if __name__ == "__main__":
    asyncio.run(main())
