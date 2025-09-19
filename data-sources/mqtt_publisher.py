#!/usr/bin/env python3
"""
MQTT Test Publisher - Sends random marine equipment test data to IoT Data Bridge periodically
"""

import asyncio
import json
import signal
import sys
from aiomqtt import Client
from data_generator import generate_random_test_data


# 전역 변수로 실행 상태 관리
running = True


def signal_handler(signum, frame):
    """Signal handler for graceful shutdown"""
    global running
    print("\nShutting down data publisher...")
    running = False


async def publish_test_data(broker_host, broker_port):
    """Publish random test data to MQTT broker periodically"""
    
    # MQTT broker settings
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