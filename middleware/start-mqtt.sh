#!/bin/bash
# Middleware Start Script for Linux/macOS - MQTT Only

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "   IoT Data Bridge - Middleware (MQTT)"
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
echo "Checking for required packages: aiomqtt, pydantic, structlog, pyyaml..."

# Check each required package
MISSING_PACKAGES=0
if ! python3 -c "import aiomqtt" &> /dev/null; then
    MISSING_PACKAGES=1
fi

if ! python3 -c "import pydantic" &> /dev/null; then
    MISSING_PACKAGES=1
fi

if ! python3 -c "import structlog" &> /dev/null; then
    MISSING_PACKAGES=1
fi

if ! python3 -c "import yaml" &> /dev/null; then
    MISSING_PACKAGES=1
fi

if [ $MISSING_PACKAGES -eq 1 ]; then
    echo "Installing missing dependencies..."
    echo "Using requirements-mqtt.txt for MQTT-specific dependencies..."
    pip3 install -r requirements-mqtt.txt
    if [ $? -ne 0 ]; then
        echo "Error: Failed to install dependencies from requirements-mqtt.txt"
        echo "Trying fallback to requirements.txt..."
        pip3 install -r requirements.txt
        if [ $? -ne 0 ]; then
            echo "Error: Failed to install dependencies"
            echo "Please check your Python environment and internet connection"
            echo "You may need to run: pip3 install --upgrade pip"
            exit 1
        fi
    fi
    echo "Dependencies installed successfully!"
else
    echo "All required dependencies are already installed."
fi

echo
echo "Starting IoT Data Bridge Middleware (MQTT)..."
echo

# Start the middleware
python3 src/main_mqtt.py
