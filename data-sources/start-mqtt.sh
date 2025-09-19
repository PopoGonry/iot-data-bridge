#!/bin/bash
# Data Sources Start Script for Linux/macOS

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "   IoT Data Bridge - Data Sources"
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
if ! python3 -c "import aiomqtt" &> /dev/null; then
    echo "Installing dependencies..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "Error: Failed to install dependencies"
        exit 1
    fi
fi

echo
echo "Starting IoT Data Sources (MQTT)..."
echo
echo "Usage Examples:"
echo "   Local:    python3 mqtt_publisher.py localhost 1883"
echo "   Remote:   python3 mqtt_publisher.py 192.168.1.100 1883"
echo

# Get broker host from user
read -p "Enter MQTT broker host (default: localhost): " BROKER_HOST
BROKER_HOST=${BROKER_HOST:-localhost}

read -p "Enter MQTT broker port (default: 1883): " BROKER_PORT
BROKER_PORT=${BROKER_PORT:-1883}

echo
echo "Starting with broker: $BROKER_HOST:$BROKER_PORT"
echo

# Start the publisher
python3 mqtt_publisher.py $BROKER_HOST $BROKER_PORT

echo
