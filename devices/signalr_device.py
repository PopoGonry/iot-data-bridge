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
        
        # Remove verbose logging
        
        # Create SignalR connection
        self.connection = HubConnectionBuilder() \
            .with_url(url) \
            .build()
        
        # Register message handler for ingress messages
        self.connection.on("ingress", self._on_message_received)
        
        # Add event handlers to prevent undefined errors
        self.connection.on_open(lambda: self.logger.debug("SignalR connection opened", device_id=self.device_id))
        self.connection.on_close(lambda: self.logger.debug("SignalR connection closed", device_id=self.device_id))
        self.connection.on_error(lambda data: self.logger.error("SignalR connection error", device_id=self.device_id, error=data))
        
        try:
            # Connect to SignalR hub
            self.connection.start()
            
            # Wait a moment for connection to stabilize
            await asyncio.sleep(1)
            
            # Check if connection is still active
            if hasattr(self.connection, 'transport') and hasattr(self.connection.transport, '_ws'):
                if self.connection.transport._ws and self.connection.transport._ws.sock:
                    pass  # Connection is active
                else:
                    raise ConnectionError("SignalR connection is not active")
            
            # Join device group
            self.connection.send("JoinGroup", [group])
            
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
                self.connection.send("LeaveGroup", [group])
                
                # Disconnect
                self.connection.stop()
                self.logger.info("Disconnected from SignalR hub", device_id=self.device_id)
            except Exception as e:
                self.logger.error("Error stopping device", 
                                device_id=self.device_id, 
                                error=str(e))
    
    def _on_message_received(self, *args):
        """Handle received message from SignalR hub"""
        try:
            # SignalR messages come as a list of arguments
            if not args or len(args) < 1:
                self.logger.warning("Received empty or invalid SignalR message", args=args)
                return
            
            # First argument should be the message content
            message = args[0]
            
            # Parse message
            if isinstance(message, str):
                data = json.loads(message)
            elif isinstance(message, list) and len(message) > 0:
                # If message is a list, take the first element
                if isinstance(message[0], str):
                    data = json.loads(message[0])
                else:
                    data = message[0]
            else:
                data = message
            
            # Extract object and value
            object_name = data.get('object', '')
            value = data.get('value', '')
            timestamp = data.get('timestamp', '')
            
            self.data_count += 1
            
            # Log received data in the requested format
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_message = f"{timestamp} | INFO | Data received | device_id={self.device_id} | object={object_name} | value={value}"
            
            # Print to console
            print(log_message)
            
            # Write to log file
            log_file = Path("logs") / f"device_{self.device_id}.log"
            log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_message + '\n')
                f.flush()
            
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
        print("Usage: python signalr_device.py <device_id> [signalr_host] [signalr_port]")
        sys.exit(1)
    
    device_id = sys.argv[1]
    signalr_host = sys.argv[2] if len(sys.argv) > 2 else "localhost"
    signalr_port = sys.argv[3] if len(sys.argv) > 3 else "5000"
    
    # Group name is same as device ID
    group_name = device_id
    
    # Build SignalR URL
    signalr_url = f"http://{signalr_host}:{signalr_port}/hub"
    
    print(f"Starting IoT Device: {device_id}")
    print(f"SignalR Host: {signalr_host}")
    print(f"SignalR Port: {signalr_port}")
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
