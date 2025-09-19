#!/usr/bin/env python3
"""
SignalR Test Publisher - Sends random test data to IoT Data Bridge periodically via SignalR
"""

import asyncio
import json
import uuid
import random
import signal
import sys
from datetime import datetime
try:
    from signalrcore.hub_connection_builder import HubConnectionBuilder
    from signalrcore.hub.base_hub_connection import BaseHubConnection
    SIGNALR_AVAILABLE = True
except ImportError:
    SIGNALR_AVAILABLE = False
    HubConnectionBuilder = None
    BaseHubConnection = None


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


async def publish_test_data(hub_url, group_name):
    """Publish random test data to SignalR hub periodically"""
    
    if not SIGNALR_AVAILABLE:
        print("Error: SignalR library not available. Please install 'signalrcore'.")
        sys.exit(1)
    
    interval = 5  # 5초마다 데이터 전송
    
    print(f"Starting IoT Data Publisher (SignalR)")
    print(f"Connecting to SignalR hub at {hub_url}")
    print(f"Joining group: {group_name}")
    print(f"Interval: {interval} seconds")
    print(f"Press Ctrl+C to stop")
    print()
    
    try:
        # SignalR Hub 연결 설정
        connection = HubConnectionBuilder() \
            .with_url(hub_url) \
            .build()
        
        # 연결 시작
        connection.start()
        print("Connected to SignalR hub successfully!")
        print()
        
        # 그룹에 참여
        connection.send("JoinGroup", [group_name])
        print(f"Joined group: {group_name}")
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
                
                # SignalR로 메시지 전송
                connection.send("SendMessage", [group_name, "ingress", json.dumps(test_case['data'])])
            
            if running:
                print(f"Cycle #{cycle_count} completed successfully!")
                print(f"Waiting {interval} seconds for next cycle...")
                print("-" * 50)
                
                # Wait for next cycle
                await asyncio.sleep(interval)
        
        # 그룹에서 나가기
        connection.send("LeaveGroup", [group_name])
        connection.stop()
        print("Data publisher stopped.")
        
    except Exception as e:
        print(f"Error: {e}")
        print(f"Make sure SignalR hub is running on {hub_url}")


async def main():
    """Main function with command line arguments"""
    if len(sys.argv) < 2:
        print("Error: SignalR hub host is required!")
        print("Usage: python signalr_publisher.py <signalr_host> [signalr_port]")
        print("Example: python signalr_publisher.py localhost 5000")
        print("Example: python signalr_publisher.py 192.168.1.100 5000")
        sys.exit(1)
    
    signalr_host = sys.argv[1]
    signalr_port = sys.argv[2] if len(sys.argv) > 2 else "5000"
    
    # Build SignalR URL
    hub_url = f"http://{signalr_host}:{signalr_port}/hub"
    
    # Group name is always iot_clients for data sources
    group_name = "iot_clients"
    
    print(f"SignalR Host: {signalr_host}")
    print(f"SignalR Port: {signalr_port}")
    print(f"SignalR URL: {hub_url}")
    print(f"Group: {group_name}")
    
    await publish_test_data(hub_url, group_name)


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
