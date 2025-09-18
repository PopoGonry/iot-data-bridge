#!/bin/bash
# IoT Device Start Script

echo "Starting IoT Device..."

# Check if device ID is provided
if [ $# -eq 0 ]; then
    echo "Usage: ./start.sh <device_id> [config_file]"
    echo "Example: ./start.sh VM-A"
    echo "Example: ./start.sh VM-A device_config.yaml"
    exit 1
fi

DEVICE_ID=$1
CONFIG_FILE=${2:-"device_config.yaml"}

echo "Starting device: $DEVICE_ID"
echo "Config file: $CONFIG_FILE"

# Start device
python device.py $DEVICE_ID $CONFIG_FILE
