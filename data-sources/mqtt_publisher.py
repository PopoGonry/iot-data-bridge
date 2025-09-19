#!/usr/bin/env python3
"""
MQTT Test Publisher - Sends random test data to IoT Data Bridge periodically
"""

import asyncio
import json
import uuid
import random
import signal
import sys
from datetime import datetime
from aiomqtt import Client


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


# 전역 변수로 실행 상태 관리
running = True


def signal_handler(signum, frame):
    """Signal handler for graceful shutdown"""
    global running
    print("\nShutting down data publisher...")
    running = False


async def publish_test_data(broker_host, broker_port):
    """Publish random test data to MQTT broker periodically"""
    
    topic = "iot/ingress"
    interval = 5  # 5초마다 데이터 전송
    
    print(f"Starting IoT Data Publisher")
    print(f"Connecting to MQTT broker at {broker_host}:{broker_port}")
    print(f"Publishing to topic: {topic}")
    print(f"Interval: {interval} seconds")
    print(f"Press Ctrl+C to stop")
    print()
    
    try:
        async with Client(hostname=broker_host, port=broker_port) as client:
            print("Connected to MQTT broker successfully!")
            print()
            
            cycle_count = 0
            while running:
                cycle_count += 1
                test_cases = generate_random_test_data()
                
                print(f"Cycle #{cycle_count} - Publishing {len(test_cases)} data points...")
                
                for i, test_case in enumerate(test_cases, 1):
                    if not running:
                        break
                        
                    print(f"  {i}. {test_case['name']}: {test_case['data']['payload']['VALUE']}")
                    
                    # Publish message
                    await client.publish(
                        topic,
                        payload=json.dumps(test_case['data']),
                        qos=1
                    )
                
                if running:
                    print(f"Cycle #{cycle_count} completed successfully!")
                    print(f"Waiting {interval} seconds for next cycle...")
                    print("-" * 50)
                    
                    # Wait for next cycle
                    await asyncio.sleep(interval)
            
            print("Data publisher stopped.")
            
    except Exception as e:
        print(f"Error: {e}")
        print(f"Make sure MQTT broker is running on {broker_host}:{broker_port}")


async def main():
    """Main function with command line arguments"""
    if len(sys.argv) < 2:
        print("Error: MQTT broker host is required!")
        print("Usage: python mqtt_publisher.py <broker_host> [broker_port]")
        print("Example: python mqtt_publisher.py localhost 1883")
        print("Example: python mqtt_publisher.py 192.168.1.100 1883")
        sys.exit(1)
    
    broker_host = sys.argv[1]
    broker_port = int(sys.argv[2]) if len(sys.argv) > 2 else 1883
    
    await publish_test_data(broker_host, broker_port)


if __name__ == "__main__":
    # Signal handler 등록
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        print("Goodbye!")

