#!/bin/bash
# Devices Start Script for Linux/macOS

echo "========================================"
echo "   IoT Data Bridge - Devices"
echo "========================================"
echo

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python3 is not installed or not in PATH"
    echo "Please install Python 3.11+ and try again"
    exit 1
fi

# Check if requirements are installed
echo "Checking dependencies..."
if ! python3 -c "import aiomqtt" &> /dev/null; then
    echo "Installing dependencies..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "Error: Failed to install dependencies"
        exit 1
    fi
fi

echo
echo "Starting IoT Device..."
echo
echo "Usage Examples:"
echo "   VM-A:     python3 device.py VM-A"
echo "   VM-B:     python3 device.py VM-B"
echo "   Custom:   python3 device.py MyDevice localhost 1883"
echo

# Get device ID from user
read -p "Enter Device ID (default: VM-A): " DEVICE_ID
DEVICE_ID=${DEVICE_ID:-VM-A}

read -p "Enter MQTT broker host (default: localhost): " MQTT_HOST
MQTT_HOST=${MQTT_HOST:-localhost}

read -p "Enter MQTT broker port (default: 1883): " MQTT_PORT
MQTT_PORT=${MQTT_PORT:-1883}

echo
echo "Starting Device: $DEVICE_ID with broker: $MQTT_HOST:$MQTT_PORT"
echo

# Start the device
python3 device.py $DEVICE_ID $MQTT_HOST $MQTT_PORT

echo
echo "Device stopped."
