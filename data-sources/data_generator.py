#!/usr/bin/env python3
"""
Test data generator for IoT Data Bridge - Random Data Generator
"""

import json
import uuid
import random
from datetime import datetime


def generate_random_test_data():
    """Generate random test data for all objects matching the external data format"""
    
    # 모든 오브젝트에 대한 랜덤 데이터 생성
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
                    "VALUE": round(random.uniform(37.0, 38.0), 4)  # 서울 근처 위도 범위
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
                    "VALUE": round(random.uniform(126.0, 127.0), 4)  # 서울 근처 경도 범위
                }
            }
        },
        {
            "name": "GPS Altitude",
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
                    "Message.ID": "GLL003",
                    "VALUE": round(random.uniform(0, 1000), 2)  # 고도 0-1000m
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
                    "VALUE": random.randint(1000, 6000)  # RPM 1000-6000
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
                    "VALUE": round(random.uniform(70.0, 120.0), 1)  # 엔진 온도 70-120°C
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
                    "VALUE": round(random.uniform(30.0, 90.0), 1)  # 습도 30-90%
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
                    "VALUE": round(random.uniform(-10.0, 40.0), 1)  # 환경 온도 -10~40°C
                }
            }
        }
    ]
    
    return test_cases


def generate_test_data():
    """Legacy function for backward compatibility"""
    return generate_random_test_data()


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