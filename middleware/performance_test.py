#!/usr/bin/env python3
"""
Performance Test for Optimized SignalR Middleware
"""

import asyncio
import time
import json
import sys
from pathlib import Path
from signalrcore.hub_connection_builder import HubConnectionBuilder
import structlog

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from monitoring.performance_monitor import PerformanceMonitor


class SignalRPerformanceTest:
    """Performance test for SignalR middleware"""
    
    def __init__(self, hub_url: str = "http://localhost:5000/hub", group: str = "iot_clients"):
        self.hub_url = hub_url
        self.group = group
        self.logger = structlog.get_logger("performance_test")
        self.connection = None
        self.monitor = PerformanceMonitor()
        
    async def start(self):
        """Start performance test"""
        try:
            # Connect to SignalR hub
            self.connection = HubConnectionBuilder() \
                .with_url(self.hub_url) \
                .build()
            
            self.connection.on("ingress", self._on_message)
            self.connection.start()
            
            # Join group
            self.connection.send("JoinGroup", [self.group])
            
            # Start monitoring
            await self.monitor.start()
            
            self.logger.info("Performance test started")
            
        except Exception as e:
            self.logger.error("Failed to start performance test", error=str(e))
            raise
    
    async def stop(self):
        """Stop performance test"""
        if self.connection:
            self.connection.send("LeaveGroup", [self.group])
            self.connection.stop()
        
        await self.monitor.stop()
        self.logger.info("Performance test stopped")
    
    def _on_message(self, *args):
        """Handle incoming messages"""
        try:
            self.monitor.record_message("test_client")
        except Exception as e:
            self.logger.error("Error processing message", error=str(e))
    
    async def run_load_test(self, duration_seconds: int = 60, messages_per_second: int = 100):
        """Run load test"""
        self.logger.info(f"Starting load test: {duration_seconds}s, {messages_per_second} msg/s")
        
        start_time = time.time()
        message_count = 0
        
        try:
            while time.time() - start_time < duration_seconds:
                # Send batch of messages
                batch_size = min(messages_per_second, 20)  # Send in batches of up to 20
                
                for _ in range(batch_size):
                    test_message = {
                        "header": {
                            "UUID": f"test-{message_count}",
                            "TIME": str(int(time.time())),
                            "SRC": "PERF-TEST",
                            "DEST": "IoTDataBridge",
                            "TYPE": "PERFTEST"
                        },
                        "payload": {
                            "Equip.Tag": "TEST001",
                            "Message.ID": "TEST001",
                            "VALUE": message_count
                        }
                    }
                    
                    # Send message
                    self.connection.send("SendMessage", [
                        self.group,
                        "ingress",
                        json.dumps(test_message)
                    ])
                    
                    message_count += 1
                    self.monitor.record_message("test_sender")
                
                # Wait for next batch
                await asyncio.sleep(1.0 / (messages_per_second / batch_size))
                
        except Exception as e:
            self.logger.error("Error in load test", error=str(e))
        
        # Get final metrics
        metrics = self.monitor.get_current_metrics()
        self.logger.info("Load test completed", **metrics)
        
        return metrics


async def main():
    """Main performance test"""
    test = SignalRPerformanceTest()
    
    try:
        await test.start()
        
        # Run load test
        metrics = await test.run_load_test(
            duration_seconds=60,
            messages_per_second=100
        )
        
        print("\n=== Performance Test Results ===")
        print(f"Total messages sent: {metrics['total_messages']}")
        print(f"Message rate: {metrics['message_rate_per_second']:.2f} msg/s")
        print(f"Total errors: {metrics['total_errors']}")
        print(f"CPU usage: {metrics['system_cpu_percent']:.2f}%")
        print(f"Memory usage: {metrics['system_memory_percent']:.2f}%")
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Test failed: {e}")
    finally:
        await test.stop()


if __name__ == "__main__":
    asyncio.run(main())
