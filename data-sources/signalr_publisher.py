#!/usr/bin/env python3
"""
SignalR Data Publisher - Publishes test data to SignalR Hub
"""

import asyncio
import json
import random
import time
import uuid
import datetime
from typing import Dict, Any
import structlog

try:
    from signalrcore.hub_connection_builder import HubConnectionBuilder
    SIGNALR_AVAILABLE = True
except ImportError as e:
    print(f"SignalR import error: {e}")
    SIGNALR_AVAILABLE = False
    HubConnectionBuilder = None


class SignalRDataPublisher:
    """SignalR data publisher with optimized batch processing"""
    
    def __init__(self, hub_url: str, group: str = "data-source"):
        self.hub_url = hub_url
        self.group = group
        self.logger = structlog.get_logger("signalr_publisher")
        self.connection = None
        self.is_running = False
        self.message_count = 0
        self.batch_size = 5  # Send messages in batches
        self.batch_timeout = 2.0  # Flush batch after 2 seconds
        self.message_buffer = []
        self._batch_task = None
        
    async def start(self):
        """Start SignalR connection"""
        if not SIGNALR_AVAILABLE:
            self.logger.error("SignalR is not available. Please install signalrcore library.")
            raise ImportError("SignalR library not available")
        
        try:
            # Build connection with optimized settings
            self.connection = HubConnectionBuilder() \
                .with_url(self.hub_url) \
                .with_automatic_reconnect([0, 2000, 10000, 30000]) \
                .build()
            
            # Register connection event handlers
            self.connection.on_open(lambda: self.logger.info("SignalR connection opened"))
            self.connection.on_close(lambda: self.logger.info("SignalR connection closed"))
            self.connection.on_error(lambda data: self.logger.error("SignalR connection error", error=str(data)))
            
            # Start connection
            self.connection.start()
            
            # Wait for connection to stabilize
            await asyncio.sleep(2)
            
            # Join group
            self.connection.send("JoinGroup", [self.group])
            
            # Start batch processing task
            self._batch_task = asyncio.create_task(self._process_batch())
            
            self.is_running = True
            self.logger.info("SignalR data publisher started", hub_url=self.hub_url, group=self.group)
            
        except Exception as e:
            import traceback
            self.logger.error("Failed to start SignalR publisher", error=str(e))
            self.logger.error("SignalR publisher traceback", traceback=traceback.format_exc())
            raise
    
    async def stop(self):
        """Stop SignalR connection"""
        self.is_running = False
        
        # Cancel batch task
        if self._batch_task:
            self._batch_task.cancel()
            try:
                await self._batch_task
            except asyncio.CancelledError:
                pass
        
        # Send remaining messages in buffer
        if self.message_buffer:
            await self._flush_buffer()
        
        if self.connection:
            try:
                self.connection.send("LeaveGroup", [self.group])
                self.connection.stop()
            except Exception as e:
                self.logger.error("Error stopping SignalR connection", error=str(e))
        
        self.logger.info("SignalR data publisher stopped")
    
    async def _process_batch(self):
        """Process message batch periodically"""
        while self.is_running:
            try:
                await asyncio.sleep(self.batch_timeout)
                if self.message_buffer:
                    await self._flush_buffer()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Error in batch processing", error=str(e))
    
    async def _flush_buffer(self):
        """Flush message buffer and send all messages"""
        if not self.message_buffer:
            return
        
        messages = self.message_buffer.copy()
        self.message_buffer.clear()
        
        try:
            # Send batch messages
            self.connection.send("SendBatchMessages", [
                self.group, 
                "ingress", 
                json.dumps(messages)
            ])
            
            self.logger.debug("SignalR batch sent", count=len(messages))
            
        except Exception as e:
            self.logger.error("Error sending SignalR batch", error=str(e))
    
    def generate_marine_data(self) -> Dict[str, Any]:
        """Generate random marine equipment test data"""
        equipment_types = [
            "engine", "generator", "pump", "compressor", "valve", 
            "sensor", "actuator", "controller", "monitor", "alarm"
        ]
        
        equipment_id = f"EQ-{random.randint(1000, 9999)}"
        equipment_type = random.choice(equipment_types)
        
        # Generate realistic marine equipment data
        data = {
            "equipment_id": equipment_id,
            "equipment_type": equipment_type,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "location": {
                "vessel": f"VESSEL-{random.randint(1, 10)}",
                "deck": random.choice(["main", "upper", "lower", "engine"]),
                "compartment": f"COMP-{random.randint(1, 20)}"
            },
            "measurements": {
                "temperature": round(random.uniform(15.0, 85.0), 2),
                "pressure": round(random.uniform(0.5, 15.0), 2),
                "vibration": round(random.uniform(0.1, 5.0), 3),
                "rpm": random.randint(500, 3000),
                "voltage": round(random.uniform(220.0, 480.0), 1),
                "current": round(random.uniform(1.0, 50.0), 2)
            },
            "status": {
                "operational": random.choice([True, True, True, False]),  # 75% operational
                "maintenance_due": random.choice([True, False, False, False]),  # 25% maintenance due
                "alarm_active": random.choice([True, False, False, False, False])  # 20% alarm
            },
            "metadata": {
                "data_source": "signalr_publisher",
                "batch_id": str(uuid.uuid4()),
                "sequence": self.message_count
            }
        }
        
        return data
    
    async def publish_data(self):
        """Publish test data continuously"""
        heartbeat_counter = 0
        
        while self.is_running:
            try:
                # Generate marine equipment data
                data = self.generate_marine_data()
                
                # Add to buffer
                self.message_buffer.append(data)
                self.message_count += 1
                
                # Send heartbeat message every 5 cycles
                heartbeat_counter += 1
                if heartbeat_counter >= 5:
                    heartbeat_counter = 0
                    print(f"💓 DATA SOURCE HEARTBEAT - Published {self.message_count} messages")
                
                # If buffer is full, send immediately
                if len(self.message_buffer) >= self.batch_size:
                    await self._flush_buffer()
                
                # Wait before next message
                await asyncio.sleep(5)  # 5 second interval
                
            except Exception as e:
                self.logger.error("Error publishing data", error=str(e))
                await asyncio.sleep(1)


async def main():
    """Main function"""
    print("🚀 Starting SignalR Data Publisher...")
    
    # Configuration
    hub_url = "http://localhost:5000/hub"
    group = "data-source"
    
    # Create publisher
    publisher = SignalRDataPublisher(hub_url, group)
    
    try:
        # Start publisher
        await publisher.start()
        
        # Start data publishing
        publish_task = asyncio.create_task(publisher.publish_data())
        
        # Wait for completion
        await publish_task
        
    except KeyboardInterrupt:
        print("\n🛑 Stopping SignalR Data Publisher...")
    except Exception as e:
        import traceback
        print(f"❌ Error: {e}")
        print(f"Traceback: {traceback.format_exc()}")
    finally:
        await publisher.stop()


if __name__ == "__main__":
    asyncio.run(main())