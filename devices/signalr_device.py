#!/usr/bin/env python3
"""
IoT Device (SignalR) - Simulates a device receiving data from middleware via SignalR
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import structlog
try:
    from signalrcore.hub_connection_builder import HubConnectionBuilder
    from signalrcore.hub.base_hub_connection import BaseHubConnection
    SIGNALR_AVAILABLE = True
except ImportError:
    SIGNALR_AVAILABLE = False
    HubConnectionBuilder = None
    BaseHubConnection = None


class IoTDevice:
    """IoT Device that receives data from middleware via SignalR"""
    
    def __init__(self, device_id: str, config: Dict[str, Any]):
        self.device_id = device_id
        self.config = config
        self.connection: Optional[BaseHubConnection] = None
        self.is_running = False
        self.data_count = 0
        self.logger = structlog.get_logger(f"device_{device_id}")
    
    async def start(self):
        """Start the device"""
        if not SIGNALR_AVAILABLE:
            self.logger.error("SignalR is not available. Please install signalrcore library.")
            raise ImportError("SignalR library not available")
        
        # Get SignalR settings
        signalr_config = self.config.get('signalr', {})
        url = signalr_config.get('url', 'http://localhost:5000/hub')
        group = signalr_config.get('group', self.device_id)
        target = signalr_config.get('target', 'ingress')
        
        self.logger.info("Starting device", 
                       device_id=self.device_id,
                       url=url,
                       group=group,
                       target=target)
        
        # Create SignalR connection
        self.connection = HubConnectionBuilder() \
            .with_url(url) \
            .build()
        
        # Register message handler
        self.connection.on("ReceiveMessage", self._on_message_received)
        
        try:
            # Connect to SignalR hub
            await self.connection.start()
            self.logger.info("Connected to SignalR hub", device_id=self.device_id)
            
            # Join device group
            await self.connection.invoke("JoinGroup", group)
            self.logger.info("Joined group", device_id=self.device_id, group=group)
            
            self.is_running = True
            
            # Keep connection alive
            while self.is_running:
                await asyncio.sleep(1)
                
        except Exception as e:
            self.logger.error("Failed to start device", 
                            device_id=self.device_id, 
                            error=str(e))
            raise
    
    async def stop(self):
        """Stop the device"""
        self.is_running = False
        
        if self.connection:
            try:
                # Leave group
                signalr_config = self.config.get('signalr', {})
                group = signalr_config.get('group', self.device_id)
                await self.connection.invoke("LeaveGroup", group)
                
                # Disconnect
                await self.connection.stop()
                self.logger.info("Disconnected from SignalR hub", device_id=self.device_id)
            except Exception as e:
                self.logger.error("Error stopping device", 
                                device_id=self.device_id, 
                                error=str(e))
    
    async def _on_message_received(self, group: str, target: str, message: str):
        """Handle received message from SignalR hub"""
        try:
            # Parse message
            data = json.loads(message)
            
            # Extract object and value
            object_name = data.get('object', '')
            value = data.get('value', '')
            timestamp = data.get('timestamp', '')
            
            self.data_count += 1
            
            # Log received data
            self.logger.info("Data received", 
                           device_id=self.device_id,
                           object=object_name,
                           value=value,
                           count=self.data_count)
            
            # Store data point (simple in-memory storage)
            self._store_data_point(object_name, value, timestamp)
            
        except json.JSONDecodeError as e:
            self.logger.error("Failed to parse message", 
                            device_id=self.device_id,
                            message=message,
                            error=str(e))
        except Exception as e:
            self.logger.error("Error processing message", 
                            device_id=self.device_id,
                            error=str(e))
    
    def _store_data_point(self, object_name: str, value: Any, timestamp: str):
        """Store data point (simple implementation)"""
        # In a real device, this would store to database, file, etc.
        # For now, just log the storage action
        self.logger.debug("Data stored", 
                        device_id=self.device_id,
                        object=object_name,
                        value=value,
                        timestamp=timestamp)


async def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python signalr_device.py <device_id> [signalr_url] [group_name]")
        sys.exit(1)
    
    device_id = sys.argv[1]
    signalr_url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:5000/hub"
    group_name = sys.argv[3] if len(sys.argv) > 3 else device_id
    
    print(f"Starting IoT Device: {device_id}")
    print(f"SignalR URL: {signalr_url}")
    print(f"Group: {group_name}")
    
    # Create configuration from command line arguments
    config = {
        'device_id': device_id,
        'signalr': {
            'url': signalr_url,
            'group': group_name,
            'target': 'ingress'
        },
        'logging': {
            'level': 'INFO',
            'file': 'device.log',
            'max_size': 10485760,
            'backup_count': 5
        }
    }
    
    print(f"Device {device_id} configuration:")
    print(f"  - SignalR URL: {config['signalr']['url']}")
    print(f"  - Group: {config['signalr']['group']}")
    
    # Setup logging
    import logging
    from logging.handlers import RotatingFileHandler
    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / config.get('logging', {}).get('file', 'device.log')
    file_handler = RotatingFileHandler(log_file, maxBytes=config.get('logging', {}).get('max_size', 10485760), backupCount=config.get('logging', {}).get('backup_count', 5), encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter('%(asctime)s | INFO | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    console_formatter = logging.Formatter('%(asctime)s | %(levelname)-5s | %(message)s', datefmt='%H:%M:%S')
    file_handler.setFormatter(file_formatter)
    console_handler.setFormatter(console_formatter)
    logging.basicConfig(level=logging.INFO, handlers=[file_handler, console_handler], force=True)
    
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
            return f"{message} | device_id={device_id} | object={object_name} | value={value}"
        elif device_id:
            return f"{message} | device_id={device_id}"
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
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        print("Goodbye!")
