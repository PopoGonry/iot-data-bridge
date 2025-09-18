#!/usr/bin/env python3
"""
Test data generator for IoT Data Bridge
"""

import json
import uuid
from datetime import datetime


def generate_test_data():
    """Generate test data matching the external data format"""
    
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
        },
        {
            "name": "Environment Humidity",
            "data": {
                "header": {
                    "UUID": str(uuid.uuid4()),
                    "TIME": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "SRC": "ENV-GW-01",
                    "DEST": "IoTDataBridge",
                    "TYPE": "ENVDATA"
                },
                "payload": {
                    "Equip.Tag": "SENSOR001",
                    "Message.ID": "HUM001",
                    "VALUE": 65.2
                }
            }
        },
        {
            "name": "Environment Temperature",
            "data": {
                "header": {
                    "UUID": str(uuid.uuid4()),
                    "TIME": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "SRC": "ENV-GW-01",
                    "DEST": "IoTDataBridge",
                    "TYPE": "ENVDATA"
                },
                "payload": {
                    "Equip.Tag": "SENSOR001",
                    "Message.ID": "TEMP001",
                    "VALUE": 23.8
                }
            }
        }
    ]
    
    return test_cases


def print_test_data():
    """Print test data in JSON format"""
    test_cases = generate_test_data()
    
    print("=== IoT Data Bridge Test Data ===\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"{i}. {test_case['name']}")
        print(json.dumps(test_case['data'], indent=2, ensure_ascii=False))
        print()


if __name__ == "__main__":
    print_test_data()

