#!/bin/bash
# Devices Start Script for Linux/macOS

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

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
echo "Checking Python dependencies..."
echo "Checking for required packages: aiomqtt, signalrcore, pyyaml, structlog..."

# Check each required package
MISSING_PACKAGES=0
if ! python3 -c "import aiomqtt" &> /dev/null; then
    MISSING_PACKAGES=1
fi

if ! python3 -c "import signalrcore" &> /dev/null; then
    MISSING_PACKAGES=1
fi

if ! python3 -c "import yaml" &> /dev/null; then
    MISSING_PACKAGES=1
fi

if ! python3 -c "import structlog" &> /dev/null; then
    MISSING_PACKAGES=1
fi

if [ $MISSING_PACKAGES -eq 1 ]; then
    echo "Installing missing dependencies..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "Error: Failed to install dependencies"
        echo "Please check your Python environment and internet connection"
        echo "You may need to run: pip3 install --upgrade pip"
        exit 1
    fi
    echo "Dependencies installed successfully!"
else
    echo "All required dependencies are already installed."
fi

echo
echo "Starting IoT Device (MQTT)..."
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
