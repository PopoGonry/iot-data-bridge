#!/bin/bash
# Data Source Start Script

echo "Starting Data Source..."

# Check if broker IP is provided
if [ $# -eq 0 ]; then
    echo "Usage: ./start.sh <broker_ip> [broker_port]"
    echo "Example: ./start.sh 192.168.1.100 1883"
    exit 1
fi

BROKER_IP=$1
BROKER_PORT=${2:-1883}

echo "Connecting to MQTT broker at $BROKER_IP:$BROKER_PORT"

# Start data publisher
python test_mqtt_publisher-multi-vm.py $BROKER_IP $BROKER_PORT
