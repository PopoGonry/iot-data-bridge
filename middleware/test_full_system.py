#!/usr/bin/env python3
"""
Full System Test - Test the complete IoT Data Bridge system
"""

import asyncio
import subprocess
import time
import signal
import sys
from pathlib import Path


class SystemTester:
    """Full system tester"""
    
    def __init__(self):
        self.processes = []
        self.running = False
    
    async def start_system(self):
        """Start the complete system"""
        print("🚀 Starting IoT Data Bridge System Test")
        print("=" * 50)
        
        # Start MQTT broker
        print("1. Starting MQTT broker...")
        await self._start_mqtt_broker()
        
        # Start SignalR Hub (if .NET is available)
        print("2. Starting SignalR Hub...")
        await self._start_signalr_hub()
        
        # Wait for services to start
        print("3. Waiting for services to start...")
        await asyncio.sleep(3)
        
        # Start IoT Data Bridge
        print("4. Starting IoT Data Bridge...")
        await self._start_iot_bridge()
        
        # Wait for IoT Data Bridge to start
        await asyncio.sleep(2)
        
        # Start all devices
        print("5. Starting all VM devices...")
        await self._start_devices()
        
        # Wait for devices to start
        await asyncio.sleep(2)
        
        print("\n✅ All services started successfully!")
        print("System is ready for testing.")
        print("\nPress Ctrl+C to stop all services")
        
        self.running = True
        
        # Keep running
        try:
            while self.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Shutting down system...")
            await self.stop_system()
    
    async def _start_mqtt_broker(self):
        """Start MQTT broker"""
        try:
            # Check if mosquitto is available
            result = subprocess.run(['mosquitto', '--help'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                # Start mosquitto
                process = subprocess.Popen([
                    'mosquitto', '-c', 'mosquitto.conf', '-d'
                ])
                self.processes.append(process)
                print("   ✓ MQTT broker started")
            else:
                print("   ⚠ MQTT broker not found, skipping...")
        except FileNotFoundError:
            print("   ⚠ MQTT broker not found, skipping...")
    
    async def _start_signalr_hub(self):
        """Start SignalR Hub"""
        try:
            # Check if dotnet is available
            result = subprocess.run(['dotnet', '--version'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                # Start SignalR Hub
                process = subprocess.Popen([
                    'dotnet', 'run'
                ], cwd='signalr_hub')
                self.processes.append(process)
                print("   ✓ SignalR Hub started")
            else:
                print("   ⚠ .NET not found, skipping SignalR Hub...")
        except FileNotFoundError:
            print("   ⚠ .NET not found, skipping SignalR Hub...")
    
    async def _start_iot_bridge(self):
        """Start IoT Data Bridge"""
        try:
            process = subprocess.Popen([
                sys.executable, 'src/main.py'
            ])
            self.processes.append(process)
            print("   ✓ IoT Data Bridge started")
        except Exception as e:
            print(f"   ✗ Failed to start IoT Data Bridge: {e}")
    
    async def _start_devices(self):
        """Start all devices"""
        try:
            process = subprocess.Popen([
                sys.executable, 'devices/start_all_devices.py'
            ])
            self.processes.append(process)
            print("   ✓ All devices started")
        except Exception as e:
            print(f"   ✗ Failed to start devices: {e}")
    
    async def stop_system(self):
        """Stop all services"""
        self.running = False
        
        print("Stopping all services...")
        
        # Stop all processes
        for process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
                print(f"   ✓ Process {process.pid} stopped")
            except subprocess.TimeoutExpired:
                process.kill()
                print(f"   ✓ Process {process.pid} killed")
            except Exception as e:
                print(f"   ✗ Error stopping process {process.pid}: {e}")
        
        # Stop MQTT broker
        try:
            subprocess.run(['pkill', '-f', 'mosquitto'], 
                         capture_output=True)
            print("   ✓ MQTT broker stopped")
        except:
            pass
        
        print("✅ All services stopped")


async def main():
    """Main function"""
    tester = SystemTester()
    
    try:
        await tester.start_system()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

