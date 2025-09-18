#!/usr/bin/env python3
"""
MQTT Test Publisher - Sends test data to IoT Data Bridge
"""

import asyncio
import json
import uuid
from datetime import datetime
from aiomqtt import Client


async def publish_test_data():
    """Publish test data to MQTT broker"""
    
    # Test data matching the external data format
    test_cases = [
        {
            "name": "GPS Latitude",
            "data": {
                "header": {
                    "UUID": str(uuid.uuid4()),
                    "TIME": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "SRC": "SENSOR-GW-01",
                    "DEST": "IoTDataBridge",
                    "TYPE": "SENSORDATA"
                },
                "payload": {
                    "Equip.Tag": "GPS001",
                    "Message.ID": "GLL001",
                    "VALUE": 37.5665
                }
            }
        },
        {
            "name": "GPS Longitude",
            "data": {
                "header": {
                    "UUID": str(uuid.uuid4()),
                    "TIME": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "SRC": "SENSOR-GW-01",
                    "DEST": "IoTDataBridge",
                    "TYPE": "SENSORDATA"
                },
                "payload": {
                    "Equip.Tag": "GPS001",
                    "Message.ID": "GLL002",
                    "VALUE": 126.9780
                }
            }
        },
        {
            "name": "Engine RPM",
            "data": {
                "header": {
                    "UUID": str(uuid.uuid4()),
                    "TIME": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "SRC": "ENGINE-GW-01",
                    "DEST": "IoTDataBridge",
                    "TYPE": "ENGINEDATA"
                },
                "payload": {
                    "Equip.Tag": "ENG001",
                    "Message.ID": "RPM001",
                    "VALUE": 2500
                }
            }
        },
        {
            "name": "Engine Temperature",
            "data": {
                "header": {
                    "UUID": str(uuid.uuid4()),
                    "TIME": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "SRC": "ENGINE-GW-01",
                    "DEST": "IoTDataBridge",
                    "TYPE": "ENGINEDATA"
                },
                "payload": {
                    "Equip.Tag": "ENG001",
                    "Message.ID": "TEMP001",
                    "VALUE": 85.5
                }
            }
        }
    ]
    
    # MQTT broker settings
    broker_host = "localhost"
    broker_port = 1883
    topic = "iot/ingress"
    
    print(f"Connecting to MQTT broker at {broker_host}:{broker_port}")
    print(f"Publishing to topic: {topic}")
    print()
    
    try:
        async with Client(hostname=broker_host, port=broker_port) as client:
            print("Connected to MQTT broker successfully!")
            print()
            
            for i, test_case in enumerate(test_cases, 1):
                print(f"{i}. Publishing: {test_case['name']}")
                print(f"   Data: {json.dumps(test_case['data'], indent=2)}")
                
                # Publish message
                await client.publish(
                    topic,
                    payload=json.dumps(test_case['data']),
                    qos=1
                )
                
                print(f"   ✓ Published successfully")
                print()
                
                # Wait between messages
                await asyncio.sleep(2)
            
            print("All test data published successfully!")
            
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure MQTT broker is running on localhost:1883")


if __name__ == "__main__":
    asyncio.run(publish_test_data())

