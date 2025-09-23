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
from layers.transports_signalr import TransportLayer
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
            hub_started = await self._start_signalr_hub()
            if not hub_started:
                print("❌ SignalR hub failed to start. Trying alternative approaches...")
                
                # Try manual start with different options
                try:
                    print("   🔄 Trying manual dotnet start...")
                    import subprocess
                    import os
                    
                    # Try to start with explicit configuration
                    signalr_hub_dir = Path("signalr_hub")
                    if signalr_hub_dir.exists():
                        print(f"   📁 Found signalr_hub directory: {signalr_hub_dir.absolute()}")
                        
                        # Try with explicit port binding
                        env = os.environ.copy()
                        env['ASPNETCORE_URLS'] = 'http://localhost:5000'
                        env['ASPNETCORE_ENVIRONMENT'] = 'Development'
                        
                        manual_result = subprocess.Popen([
                            "dotnet", "run", "--urls", "http://localhost:5000"
                        ], cwd=str(signalr_hub_dir), env=env, 
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                        
                        # Wait a bit and check
                        await asyncio.sleep(3)
                        
                        if manual_result.poll() is None:
                            print("   ✅ Manual start successful")
                            if await self._verify_hub_connection():
                                print("✅ SignalR hub is now responding on port 5000")
                                hub_started = True
                            else:
                                print("   ⚠️  Manual start succeeded but hub not responding")
                        else:
                            stdout, stderr = manual_result.communicate()
                            print(f"   ❌ Manual start failed:")
                            print(f"STDOUT: {stdout}")
                            print(f"STDERR: {stderr}")
                            
                except Exception as e:
                    print(f"   ❌ Manual start attempt failed: {e}")
                
                if not hub_started:
                    print("⚠️  Continuing without SignalR hub...")
                    print("💡 You can try starting the hub manually:")
                    print("   cd middleware/signalr_hub")
                    print("   dotnet run")
            
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
        
        # Initialize resolver layer
        self.resolver_layer = ResolverLayer(
            self.device_catalog,
            self._handle_resolved_event
        )
        
        # Initialize transports layer
        self.transports_layer = TransportLayer(
            self.config.transports,
            self.device_catalog,
            self._handle_device_ingest
        )
        
        # Initialize logging layer
        self.logging_layer = LoggingLayer(
            self.config.logging
        )
        
        # Set up layer callbacks
        self.resolver_layer.set_transports_callback(self._handle_resolved_event)
    
    async def _start_signalr_hub(self):
        """Start SignalR hub asynchronously"""
        import subprocess
        import os
        import asyncio
        
        try:
            # Stop any existing dotnet processes more aggressively
            try:
                print("Stopping any existing SignalR hubs...")
                # Try multiple methods to stop dotnet processes
                subprocess.run(["pkill", "-f", "dotnet"], check=False, capture_output=True)
                subprocess.run(["pkill", "dotnet"], check=False, capture_output=True)
                subprocess.run(["killall", "dotnet"], check=False, capture_output=True)
                
                # Wait for processes to stop
                await asyncio.sleep(2)
                
                # Check if port 5000 is still in use
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex(('localhost', 5000))
                sock.close()
                
                if result == 0:
                    print("Port 5000 is still in use, trying to force kill...")
                    # Force kill any process using port 5000
                    try:
                        # Try fuser first
                        subprocess.run(["fuser", "-k", "5000/tcp"], check=False, capture_output=True)
                        await asyncio.sleep(1)
                        
                        # If still in use, try to find and kill the process using netstat/lsof
                        try:
                            # Find process using port 5000
                            result = subprocess.run(["netstat", "-tlnp"], capture_output=True, text=True)
                            for line in result.stdout.split('\n'):
                                if ':5000' in line and 'LISTEN' in line:
                                    parts = line.split()
                                    if len(parts) > 6:
                                        pid_info = parts[6]
                                        if '/' in pid_info:
                                            pid = pid_info.split('/')[0]
                                            print(f"Killing process {pid} using port 5000")
                                            subprocess.run(["kill", "-9", pid], check=False, capture_output=True)
                                            await asyncio.sleep(1)
                        except:
                            pass
                            
                        # Try lsof as alternative
                        try:
                            result = subprocess.run(["lsof", "-ti:5000"], capture_output=True, text=True)
                            if result.stdout.strip():
                                pids = result.stdout.strip().split('\n')
                                for pid in pids:
                                    if pid.strip():
                                        print(f"Killing process {pid} using port 5000 (lsof)")
                                        subprocess.run(["kill", "-9", pid.strip()], check=False, capture_output=True)
                                        await asyncio.sleep(1)
                        except:
                            pass
                            
                    except:
                        pass
                        
            except Exception as e:
                print(f"Warning: Error stopping existing SignalR hubs: {e}")
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
                return False
            
            # Wait longer for processes to fully stop and port to be released
            print("   ⏳ Waiting for port to be fully released...")
            await asyncio.sleep(5)
            
            # Final check if port 5000 is available with retries and detailed diagnostics
            max_retries = 5
            for retry in range(max_retries):
                # Check port availability - connect_ex returns 0 if connection successful (port in use)
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', 5000))
                sock.close()
                
                if result == 0:
                    print(f"❌ Port 5000 is still in use (attempt {retry + 1}/{max_retries})")
                    
                    # Show what's using the port
                    try:
                        # Check with netstat
                        netstat_result = subprocess.run(["netstat", "-tlnp"], capture_output=True, text=True)
                        for line in netstat_result.stdout.split('\n'):
                            if ':5000' in line and 'LISTEN' in line:
                                print(f"   📍 Port 5000 is being used by: {line}")
                        
                        # Check with lsof
                        lsof_result = subprocess.run(["lsof", "-i:5000"], capture_output=True, text=True)
                        if lsof_result.stdout.strip():
                            print(f"   📍 lsof shows: {lsof_result.stdout.strip()}")
                        
                        # Check with ss
                        ss_result = subprocess.run(["ss", "-tlnp"], capture_output=True, text=True)
                        for line in ss_result.stdout.split('\n'):
                            if ':5000' in line:
                                print(f"   📍 ss shows: {line}")
                                
                    except Exception as e:
                        print(f"   ⚠️  Could not get detailed port info: {e}")
                    
                    await asyncio.sleep(2)
                else:
                    print(f"✅ Port 5000 is now available (attempt {retry + 1})")
                    break
            else:
                print("❌ Error: Port 5000 is still in use after all cleanup attempts")
                print("🔍 Detailed port information:")
                
                # Final diagnostic
                try:
                    print("\n📊 Current port 5000 status:")
                    subprocess.run(["netstat", "-tlnp"], check=False)
                    print("\n📊 lsof output:")
                    subprocess.run(["lsof", "-i:5000"], check=False)
                    print("\n📊 ss output:")
                    subprocess.run(["ss", "-tlnp"], check=False)
                except:
                    pass
                
                print("\n💡 Manual cleanup commands:")
                print("   sudo pkill -f dotnet")
                print("   sudo fuser -k 5000/tcp")
                print("   sudo netstat -tlnp | grep 5000")
                return False
            
            # Additional wait and final port check before starting SignalR hub
            print("   ⏳ Final wait before starting SignalR hub...")
            await asyncio.sleep(2)
            
            # One more port check
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            final_check = sock.connect_ex(('localhost', 5000))
            sock.close()
            
            if final_check == 0:
                print("   ❌ Port 5000 is still in use at final check, waiting more...")
                await asyncio.sleep(3)
            
            print(f"Starting SignalR hub from: {signalr_hub_dir}")
            
            # Start SignalR hub in background with more detailed output
            print(f"   🔧 Starting dotnet run in directory: {signalr_hub_dir}")
            result = subprocess.Popen([
                "dotnet", "run", "--verbosity", "normal"
            ], cwd=str(signalr_hub_dir), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            # Wait for hub to start with longer timeout
            print("   ⏳ Waiting for SignalR hub to start...")
            await asyncio.sleep(5)
            
            # Check if process is still running
            if result.poll() is None:
                print("   ✅ dotnet process is running")
                
                # Check stdout/stderr for any immediate errors
                try:
                    # Non-blocking read of available output
                    import select
                    import sys
                    
                    # Check if there's any output available
                    if hasattr(select, 'select'):
                        ready, _, _ = select.select([result.stdout, result.stderr], [], [], 0.1)
                        if ready:
                            for stream in ready:
                                if stream == result.stdout:
                                    output = stream.read()
                                    if output:
                                        print(f"   📤 STDOUT: {output}")
                                elif stream == result.stderr:
                                    output = stream.read()
                                    if output:
                                        print(f"   📤 STDERR: {output}")
                except:
                    pass
                
                # Verify hub is actually listening on port 5000 with retries
                print("   🔍 Verifying SignalR hub connection...")
                max_verification_attempts = 5
                for attempt in range(max_verification_attempts):
                    if await self._verify_hub_connection():
                        print("✅ SignalR hub started successfully and is listening on port 5000")
                        return True
                    else:
                        print(f"   ⏳ Hub not ready yet (attempt {attempt + 1}/{max_verification_attempts})")
                        await asyncio.sleep(2)
                
                print("❌ SignalR hub process started but not responding on port 5000 after verification attempts")
                
                # Get final output for debugging
                try:
                    stdout, stderr = result.communicate(timeout=1)
                    if stdout:
                        print(f"   📤 Final STDOUT: {stdout}")
                    if stderr:
                        print(f"   📤 Final STDERR: {stderr}")
                except:
                    pass
                
                return False
            else:
                stdout, stderr = result.communicate()
                print(f"❌ Failed to start SignalR hub:")
                print(f"STDOUT: {stdout}")
                print(f"STDERR: {stderr}")
                return False
                
        except FileNotFoundError:
            print("Warning: dotnet not found. Please install .NET SDK or start SignalR hub manually.")
            return False
        except Exception as e:
            print(f"Error starting SignalR hub: {e}")
            return False
    
    async def _verify_hub_connection(self):
        """Verify that SignalR hub is actually listening on port 5000"""
        import socket
        import asyncio
        import requests
        
        try:
            # Try to connect to port 5000
            def check_port():
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex(('localhost', 5000))
                sock.close()
                return result == 0
            
            # Run the check in a thread to avoid blocking
            loop = asyncio.get_event_loop()
            port_open = await loop.run_in_executor(None, check_port)
            
            if not port_open:
                return False
            
            # Try to make HTTP request to verify it's actually the SignalR hub
            try:
                def check_http():
                    response = requests.get('http://localhost:5000/health', timeout=3)
                    return response.status_code == 200 and response.text.strip() == 'OK'
                
                http_ok = await loop.run_in_executor(None, check_http)
                if http_ok:
                    return True
            except:
                pass
            
            # Fallback: try the root endpoint
            try:
                def check_root():
                    response = requests.get('http://localhost:5000/', timeout=3)
                    return response.status_code == 200 and 'SignalR Hub' in response.text
                
                root_ok = await loop.run_in_executor(None, check_root)
                if root_ok:
                    return True
            except:
                pass
            
            return False
            
        except Exception as e:
            print(f"Hub connection verification failed: {e}")
            return False
    
    async def _heartbeat_monitor(self):
        """Monitor system health and send heartbeat messages"""
        import time
        start_time = time.time()
        heartbeat_count = 0
        
        while self.is_running:
            try:
                heartbeat_count += 1
                current_time = time.time()
                uptime = current_time - start_time
                
                # Get layer statistics
                input_stats = getattr(self.input_layer, 'get_stats', lambda: {})()
                mapping_stats = getattr(self.mapping_layer, 'get_stats', lambda: {})()
                resolver_stats = getattr(self.resolver_layer, 'get_stats', lambda: {})()
                transports_stats = getattr(self.transports_layer, 'get_stats', lambda: {})()
                
                # Create heartbeat message
                heartbeat_msg = {
                    "type": "heartbeat",
                    "timestamp": current_time,
                    "uptime": uptime,
                    "heartbeat_count": heartbeat_count,
                    "layers": {
                        "input": {
                            "processed": input_stats.get('processed', 0),
                            "errors": input_stats.get('errors', 0),
                            "is_running": getattr(self.input_layer, 'is_running', False)
                        },
                        "mapping": {
                            "processed": mapping_stats.get('processed', 0),
                            "errors": mapping_stats.get('errors', 0),
                            "is_running": getattr(self.mapping_layer, 'is_running', False)
                        },
                        "resolver": {
                            "processed": resolver_stats.get('processed', 0),
                            "errors": resolver_stats.get('errors', 0),
                            "is_running": getattr(self.resolver_layer, 'is_running', False)
                        },
                        "transports": {
                            "processed": transports_stats.get('processed', 0),
                            "errors": transports_stats.get('errors', 0),
                            "is_running": getattr(self.transports_layer, 'is_running', False)
                        }
                    }
                }
                
                # Log heartbeat
                print(f"💓 HEARTBEAT #{heartbeat_count} - Uptime: {uptime:.1f}s")
                print(f"   Input: {input_stats.get('processed', 0)} processed, {input_stats.get('errors', 0)} errors")
                print(f"   Mapping: {mapping_stats.get('processed', 0)} processed, {mapping_stats.get('errors', 0)} errors")
                print(f"   Resolver: {resolver_stats.get('processed', 0)} processed, {resolver_stats.get('errors', 0)} errors")
                print(f"   Transports: {transports_stats.get('processed', 0)} processed, {transports_stats.get('errors', 0)} errors")
                
                # Check for potential issues
                if input_stats.get('errors', 0) > 10:
                    print("⚠️  WARNING: High error count in Input layer")
                if mapping_stats.get('errors', 0) > 10:
                    print("⚠️  WARNING: High error count in Mapping layer")
                if resolver_stats.get('errors', 0) > 10:
                    print("⚠️  WARNING: High error count in Resolver layer")
                if transports_stats.get('errors', 0) > 10:
                    print("⚠️  WARNING: High error count in Transports layer")
                
                # Wait for next heartbeat (30 seconds)
                await asyncio.sleep(30)
                
            except Exception as e:
                print(f"❌ Heartbeat monitor error: {e}")
                await asyncio.sleep(30)  # Continue monitoring even if there's an error
    
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
            
            # Start all layers
            await self.input_layer.start()
            await self.mapping_layer.start()
            await self.resolver_layer.start()
            await self.transports_layer.start()
            await self.logging_layer.start()
            
            # Start heartbeat monitoring
            heartbeat_task = asyncio.create_task(self._heartbeat_monitor())
            
            # Keep running with more efficient waiting
            try:
                while self.is_running:
                    # Use a longer sleep to reduce CPU usage while maintaining responsiveness
                    await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                pass
            finally:
                # Cancel heartbeat task
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass
                
        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"Error in main loop: {e}")
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


async def main():
    """Main entry point"""
    # Parse command line arguments
    config_path = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Create and initialize bridge
    bridge = IoTDataBridge(config_path)
    await bridge.initialize()
    
    # Setup signal handlers
    def signal_handler(signum, frame):
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