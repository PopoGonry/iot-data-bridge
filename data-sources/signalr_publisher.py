#!/usr/bin/env python3
"""
SignalR Test Publisher - Sends random marine equipment test data to IoT Data Bridge periodically via SignalR
"""

import asyncio
import json
import signal
import sys
try:
    from signalrcore.hub_connection_builder import HubConnectionBuilder
    from signalrcore.hub.base_hub_connection import BaseHubConnection
    SIGNALR_AVAILABLE = True
except ImportError:
    SIGNALR_AVAILABLE = False
    HubConnectionBuilder = None
    BaseHubConnection = None

from data_generator import generate_random_test_data


# 전역 변수로 실행 상태 관리
running = True


def signal_handler(signum, frame):
    """Signal handler for graceful shutdown"""
    global running
    print("\nShutting down data publisher...")
    running = False
    # 강제 종료를 위한 추가 처리
    import os
    os._exit(0)


async def publish_test_data(hub_url, group_name):
    """Publish random test data to SignalR hub periodically"""
    
    if not SIGNALR_AVAILABLE:
        print("Error: SignalR library not available. Please install 'signalrcore'.")
        sys.exit(1)
    
    interval = 5  # 5초마다 데이터 전송
    connection = None
    
    print(f"Starting IoT Data Publisher (SignalR)")
    print(f"Connecting to SignalR hub at {hub_url}")
    print(f"Joining group: {group_name}")
    print(f"Interval: {interval} seconds")
    print(f"Press Ctrl+C to stop")
    print()
    
    try:
        # SignalR Hub 연결 설정 (단일 연결)
        connection = HubConnectionBuilder() \
            .with_url(hub_url) \
            .build()
        
        # 연결 시작
        connection.start()
        print("Connected to SignalR hub successfully!")
        print()
        
        # 연결이 안정화될 때까지 잠시 대기
        await asyncio.sleep(2)
        
        # 연결 상태 확인
        if hasattr(connection, 'transport') and hasattr(connection.transport, '_ws'):
            if connection.transport._ws and connection.transport._ws.sock:
                print("Connection is active and ready")
            else:
                print("Warning: Connection may not be fully established")
        
        # 그룹에 참여
        connection.send("JoinGroup", [group_name])
        print(f"Joined group: {group_name}")
        print()
        
        # 그룹 참여 후 잠시 대기
        await asyncio.sleep(1)
        
        cycle_count = 0
        while running:
            cycle_count += 1
            test_cases = generate_random_test_data()
            
            print(f"Cycle #{cycle_count} - Publishing {len(test_cases)} data points...")
            
            for i, test_case in enumerate(test_cases, 1):
                if not running:
                    break
                    
                print(f"  {i}. {test_case['name']}: {test_case['data']['payload']['VALUE']}")
                
                try:
                    # SignalR로 메시지 전송
                    connection.send("SendMessage", [group_name, "ingress", json.dumps(test_case['data'])])
                    # 메시지 전송 간격
                    await asyncio.sleep(0.5)
                except Exception as e:
<<<<<<< HEAD
<<<<<<< HEAD
                    print(f"Error sending batch messages, trying individual messages: {e}")
                    # 배치 전송 실패 시 개별 메시지로 전송
                    for i, message_data in enumerate(batch_messages, 1):
                        if not running:
                            break
                        try:
                            connection.send("SendMessage", [group_name, "ingress", json.dumps(message_data)])
                        except Exception as e2:
                            print(f"Error sending individual message {i}: {e2}")
                            break
=======
                    print(f"Error sending message {i}: {e}")
                    break
>>>>>>> parent of de65d42 (perf: SignalR 데이터 전송 방식)
=======
                    print(f"Error sending message {i}: {e}")
                    break
>>>>>>> parent of de65d42 (perf: SignalR 데이터 전송 방식)
            
            if running:
                print(f"Cycle #{cycle_count} completed successfully!")
                print(f"Waiting {interval} seconds for next cycle...")
                print("-" * 50)
                
                # Wait for next cycle (running 체크 포함)
                for _ in range(interval):
                    if not running:
                        break
                    await asyncio.sleep(1)
        
    except Exception as e:
        print(f"Error: {e}")
        print(f"Make sure SignalR hub is running on {hub_url}")
    finally:
        # 안전한 종료 처리
        if connection:
            try:
                print("Cleaning up SignalR connection...")
                connection.send("LeaveGroup", [group_name])
                connection.stop()
                print("Data publisher stopped.")
            except Exception as e:
                print(f"Error during cleanup: {e}")


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
    
    # Group name for data sources (separate from middleware)
    group_name = "data_sources"
    
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
