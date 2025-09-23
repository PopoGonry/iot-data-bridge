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
            if not self._start_mqtt_broker():
                print("Failed to start MQTT broker. Exiting...")
                sys.exit(1)
            
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
            
            # Show Data sent logs in console with proper format
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
                console_formatter
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
        """Start MQTT broker with proper configuration"""
        import subprocess
        import os
        import time
        import socket
        
        try:
            print("Starting MQTT broker...")
            
            # Stop any existing mosquitto processes more aggressively
            try:
                print("Stopping any existing MQTT brokers...")
                # Try multiple methods to stop mosquitto
                subprocess.run(["pkill", "-f", "mosquitto"], check=False, capture_output=True)
                subprocess.run(["pkill", "mosquitto"], check=False, capture_output=True)
                subprocess.run(["killall", "mosquitto"], check=False, capture_output=True)
                
                # Wait for processes to stop
                time.sleep(2)
                
                # Check if port 1883 is still in use
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex(('localhost', 1883))
                sock.close()
                
                if result == 0:
                    print("Port 1883 is still in use, trying to force kill...")
                    # Force kill any process using port 1883
                    try:
                        # Try fuser first
                        subprocess.run(["fuser", "-k", "1883/tcp"], check=False, capture_output=True)
                        time.sleep(1)
                        
                        # If still in use, try to find and kill the process using netstat/lsof
                        try:
                            # Find process using port 1883
                            result = subprocess.run(["netstat", "-tlnp"], capture_output=True, text=True)
                            for line in result.stdout.split('\n'):
                                if ':1883' in line and 'LISTEN' in line:
                                    parts = line.split()
                                    if len(parts) > 6:
                                        pid_info = parts[6]
                                        if '/' in pid_info:
                                            pid = pid_info.split('/')[0]
                                            print(f"Killing process {pid} using port 1883")
                                            subprocess.run(["kill", "-9", pid], check=False, capture_output=True)
                                            time.sleep(1)
                        except:
                            pass
                            
                        # Try lsof as alternative
                        try:
                            result = subprocess.run(["lsof", "-ti:1883"], capture_output=True, text=True)
                            if result.stdout.strip():
                                pids = result.stdout.strip().split('\n')
                                for pid in pids:
                                    if pid.strip():
                                        print(f"Killing process {pid} using port 1883 (lsof)")
                                        subprocess.run(["kill", "-9", pid.strip()], check=False, capture_output=True)
                                        time.sleep(1)
                        except:
                            pass
                        
                        # Try sudo methods for system processes
                        try:
                            print("   🔧 Trying sudo methods for system processes...")
                            
                            # Try stopping systemd service first
                            subprocess.run(["sudo", "systemctl", "stop", "mosquitto"], check=False, capture_output=True)
                            time.sleep(1)
                            
                            # Try sudo pkill
                            subprocess.run(["sudo", "pkill", "-f", "mosquitto"], check=False, capture_output=True)
                            time.sleep(1)
                            
                            # Try sudo fuser
                            subprocess.run(["sudo", "fuser", "-k", "1883/tcp"], check=False, capture_output=True)
                            time.sleep(1)
                            
                            # Try sudo lsof and kill
                            result = subprocess.run(["sudo", "lsof", "-ti:1883"], capture_output=True, text=True)
                            if result.stdout.strip():
                                pids = result.stdout.strip().split('\n')
                                for pid in pids:
                                    if pid.strip():
                                        print(f"   🔧 Killing system process {pid} using port 1883 (sudo lsof)")
                                        subprocess.run(["sudo", "kill", "-9", pid.strip()], check=False, capture_output=True)
                                        time.sleep(1)
                                        
                            # Try disabling the service to prevent restart
                            subprocess.run(["sudo", "systemctl", "disable", "mosquitto"], check=False, capture_output=True)
                            
                        except Exception as e:
                            print(f"   ⚠️  Sudo methods failed: {e}")
                            pass
                            
                    except:
                        pass
                        
            except Exception as e:
                print(f"Warning: Error stopping existing brokers: {e}")
                pass
            
            # Get the directory where mosquitto.conf is located
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
                print(f"Error: mosquitto.conf not found. Searched: {[str(p) for p in possible_paths]}")
                print("Please ensure mosquitto.conf exists in the middleware directory")
                return False
            
            print(f"Using MQTT config: {mosquitto_conf}")
            
            # Create mosquitto data directory if it doesn't exist
            data_dir = mosquitto_conf.parent / "mosquitto_data"
            data_dir.mkdir(exist_ok=True)
            
            # Start mosquitto with the config file
            cmd = [
                "mosquitto", 
                "-c", str(mosquitto_conf), 
                "-v"  # verbose mode for debugging
            ]
            
            # Wait longer for processes to fully stop and port to be released
            print("   ⏳ Waiting for port to be fully released...")
            time.sleep(5)
            
            # Final check if port 1883 is available with retries and detailed diagnostics
            max_retries = 5
            for retry in range(max_retries):
                # Check port availability - connect_ex returns 0 if connection successful (port in use)
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', 1883))
                sock.close()
                
                if result == 0:
                    print(f"❌ Port 1883 is still in use (attempt {retry + 1}/{max_retries})")
                    
                    # Show what's using the port
                    try:
                        # Check with netstat
                        netstat_result = subprocess.run(["netstat", "-tlnp"], capture_output=True, text=True)
                        for line in netstat_result.stdout.split('\n'):
                            if ':1883' in line and 'LISTEN' in line:
                                print(f"   📍 Port 1883 is being used by: {line}")
                        
                        # Check with lsof
                        lsof_result = subprocess.run(["lsof", "-i:1883"], capture_output=True, text=True)
                        if lsof_result.stdout.strip():
                            print(f"   📍 lsof shows: {lsof_result.stdout.strip()}")
                        
                        # Check with ss
                        ss_result = subprocess.run(["ss", "-tlnp"], capture_output=True, text=True)
                        for line in ss_result.stdout.split('\n'):
                            if ':1883' in line:
                                print(f"   📍 ss shows: {line}")
                                
                    except Exception as e:
                        print(f"   ⚠️  Could not get detailed port info: {e}")
                    
                    time.sleep(2)
                else:
                    print(f"✅ Port 1883 is now available (attempt {retry + 1})")
                    break
            else:
                print("❌ Error: Port 1883 is still in use after all cleanup attempts")
                print("🔍 Detailed port information:")
                
                # Final diagnostic
                try:
                    print("\n📊 Current port 1883 status:")
                    subprocess.run(["netstat", "-tlnp"], check=False)
                    print("\n📊 lsof output:")
                    subprocess.run(["lsof", "-i:1883"], check=False)
                    print("\n📊 ss output:")
                    subprocess.run(["ss", "-tlnp"], check=False)
                except:
                    pass
                
                print("\n💡 Manual cleanup commands:")
                print("   # Stop systemd service:")
                print("   sudo systemctl stop mosquitto")
                print("   sudo systemctl disable mosquitto")
                print("   ")
                print("   # Kill processes:")
                print("   sudo pkill -f mosquitto")
                print("   sudo fuser -k 1883/tcp")
                print("   ")
                print("   # Check what's using the port:")
                print("   sudo netstat -tlnp | grep 1883")
                print("   sudo lsof -i:1883")
                print("   ")
                print("   # If still in use, find and kill manually:")
                print("   sudo lsof -ti:1883 | xargs sudo kill -9")
                return False
            
            # Additional wait and final port check before starting mosquitto
            print("   ⏳ Final wait before starting mosquitto...")
            time.sleep(2)
            
            # One more port check
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            final_check = sock.connect_ex(('localhost', 1883))
            sock.close()
            
            if final_check == 0:
                print("   ❌ Port 1883 is still in use at final check, trying aggressive cleanup...")
                
                # Try more aggressive cleanup
                try:
                    # Kill any process using port 1883 with sudo
                    subprocess.run(["sudo", "fuser", "-k", "1883/tcp"], check=False, capture_output=True)
                    time.sleep(1)
                    
                    # Try to find and kill any remaining processes
                    result = subprocess.run(["sudo", "lsof", "-ti:1883"], capture_output=True, text=True)
                    if result.stdout.strip():
                        pids = result.stdout.strip().split('\n')
                        for pid in pids:
                            if pid.strip():
                                print(f"   🔧 Force killing PID {pid}")
                                subprocess.run(["sudo", "kill", "-9", pid.strip()], check=False, capture_output=True)
                    
                    # Wait for port to be released
                    time.sleep(3)
                    
                    # Final check
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(1)
                    final_final_check = sock.connect_ex(('localhost', 1883))
                    sock.close()
                    
                    if final_final_check == 0:
                        print("   ❌ Port 1883 still in use after aggressive cleanup")
                        print("   💡 Trying to start mosquitto on different port...")
                        # We'll try to start anyway and let mosquitto handle it
                    else:
                        print("   ✅ Port 1883 finally released!")
                        
                except Exception as e:
                    print(f"   ⚠️  Aggressive cleanup failed: {e}")
                    pass
            
            print(f"Starting mosquitto with command: {' '.join(cmd)}")
            
            # Start mosquitto in background instead of blocking
            try:
                process = subprocess.Popen(cmd, cwd=str(mosquitto_conf.parent), 
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                        text=True)
                
                # Wait a moment for mosquitto to start
                time.sleep(3)
                
                # Check if process is still running
                if process.poll() is None:
                    print("✅ MQTT broker started successfully in background")
                    return True
                else:
                    stdout, stderr = process.communicate()
                    print("❌ MQTT broker failed to start:")
                    print(f"STDOUT: {stdout}")
                    print(f"STDERR: {stderr}")
                    
                    # Check if it's a port binding issue
                    if "Address already in use" in stderr or "Address already in use" in stdout:
                        print("🔧 Port binding issue detected. Trying alternative approach...")
                        
                        # Try starting mosquitto with different options
                        try:
                            print("   🔄 Trying mosquitto with -p flag...")
                            alt_cmd = ["mosquitto", "-p", "1884", "-v"]  # Use different port
                            alt_process = subprocess.Popen(alt_cmd, cwd=str(mosquitto_conf.parent), 
                                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                                         text=True)
                            time.sleep(2)
                            
                            if alt_process.poll() is None:
                                print("✅ MQTT broker started on port 1884")
                                print("⚠️  Note: Using port 1884 instead of 1883")
                                return True
                            else:
                                alt_stdout, alt_stderr = alt_process.communicate()
                                print(f"❌ Alternative start also failed:")
                                print(f"STDOUT: {alt_stdout}")
                                print(f"STDERR: {alt_stderr}")
                                
                        except Exception as e:
                            print(f"❌ Alternative start failed: {e}")
                    
                    return False
                    
            except Exception as e:
                print(f"❌ Error starting mosquitto: {e}")
                return False
            
                
        except FileNotFoundError:
            print("Error: mosquitto not found. Please install mosquitto:")
            print("  Ubuntu/Debian: sudo apt-get install mosquitto mosquitto-clients")
            print("  CentOS/RHEL: sudo yum install mosquitto")
            print("  macOS: brew install mosquitto")
            return False
        except subprocess.TimeoutExpired:
            print("Error: MQTT broker startup timed out")
            return False
        except Exception as e:
            print(f"Error starting MQTT broker: {e}")
            return False
    
    def _verify_mqtt_broker(self):
        """Verify MQTT broker is listening on all interfaces"""
        import socket
        
        try:
            # Check if port 1883 is listening on all interfaces (0.0.0.0)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            
            # Try to connect to localhost
            result = sock.connect_ex(('127.0.0.1', 1883))
            sock.close()
            
            if result == 0:
                print("MQTT broker is listening on localhost:1883")
                
                # Also check if it's listening on all interfaces
                # by trying to connect from a different perspective
                try:
                    # Get local IP address
                    import subprocess
                    result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
                    if result.returncode == 0:
                        local_ip = result.stdout.strip().split()[0]
                        print(f"Local IP address: {local_ip}")
                        print(f"MQTT broker should be accessible at {local_ip}:1883")
                except:
                    pass
                
                return True
            else:
                print("MQTT broker is not responding on localhost:1883")
                return False
                
        except Exception as e:
            print(f"Error verifying MQTT broker: {e}")
            return False
    
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
        pass
    except Exception as e:
        print(f"Application error: {e}")
        sys.exit(1)
    finally:
        await app.stop()


if __name__ == "__main__":
    asyncio.run(main())