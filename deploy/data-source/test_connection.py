#!/usr/bin/env python3
"""
MQTT Connection Test Script
Tests MQTT broker connectivity without sending data
"""

import asyncio
import sys
from aiomqtt import Client


async def test_connection(broker_host="localhost", broker_port=1883):
    """Test MQTT broker connection"""
    
    print(f"Testing connection to MQTT broker at {broker_host}:{broker_port}")
    
    try:
        async with Client(hostname=broker_host, port=broker_port) as client:
            print("✅ Connection successful!")
            print(f"   Broker: {broker_host}:{broker_port}")
            print("   Ready to send data")
            return True
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print(f"   Make sure MQTT broker is running on {broker_host}:{broker_port}")
        return False


async def main():
    """Main function with command line arguments"""
    if len(sys.argv) > 1:
        broker_host = sys.argv[1]
        broker_port = int(sys.argv[2]) if len(sys.argv) > 2 else 1883
    else:
        broker_host = "localhost"
        broker_port = 1883
    
    success = await test_connection(broker_host, broker_port)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
