#!/usr/bin/env python3
"""
MQTT Test Subscriber - Receives data from IoT Data Bridge
"""

import asyncio
import json
from aiomqtt import Client


async def subscribe_to_devices():
    """Subscribe to device topics to receive data"""
    
    # MQTT broker settings
    broker_host = "localhost"
    broker_port = 1883
    
    # Device topics to subscribe to
    device_topics = [
        "devices/vm-a/ingress",
        "devices/vm-b/ingress", 
        "devices/vm-c/ingress",
        "devices/vm-d/ingress"
    ]
    
    print(f"Connecting to MQTT broker at {broker_host}:{broker_port}")
    print(f"Subscribing to device topics:")
    for topic in device_topics:
        print(f"  - {topic}")
    print()
    
    try:
        async with Client(hostname=broker_host, port=broker_port) as client:
            print("Connected to MQTT broker successfully!")
            
            # Subscribe to all device topics
            for topic in device_topics:
                await client.subscribe(topic, qos=1)
                print(f"✓ Subscribed to {topic}")
            
            print()
            print("Waiting for messages... (Press Ctrl+C to stop)")
            print("=" * 50)
            
            # Listen for messages
            async for message in client.messages:
                try:
                    # Parse message payload
                    payload = json.loads(message.payload.decode('utf-8'))
                    
                    print(f"📨 Received from {message.topic}")
                    print(f"   Object: {payload.get('object')}")
                    print(f"   Value: {payload.get('value')}")
                    print(f"   Timestamp: {payload.get('timestamp')}")
                    print()
                    
                except json.JSONDecodeError as e:
                    print(f"❌ Invalid JSON in message from {message.topic}: {e}")
                except Exception as e:
                    print(f"❌ Error processing message from {message.topic}: {e}")
                    
    except KeyboardInterrupt:
        print("\n👋 Subscriber stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure MQTT broker is running on localhost:1883")


if __name__ == "__main__":
    asyncio.run(subscribe_to_devices())
