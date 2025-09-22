#!/bin/bash
# IoT Data Bridge Middleware Server Start Script (MQTT Only)

# Change to script directory
cd "$(dirname "$0")"

echo "========================================"
echo "   IoT Data Bridge - Middleware (MQTT Only)"
echo "========================================"
echo

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python3 is not installed or not in PATH"
    echo "Please install Python 3.11+ and try again"
    exit 1
fi

echo "Starting IoT Data Bridge Middleware Server (MQTT Only)..."
echo "Working directory: $(pwd)"

# Check if virtual environment exists and activate it
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
elif [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
elif [ -n "$VIRTUAL_ENV" ]; then
    echo "Virtual environment already active: $VIRTUAL_ENV"
else
    echo "Warning: No virtual environment found. Using system Python."
fi

# Create logs directory
mkdir -p logs

# Create mosquitto_data directory for MQTT broker persistence
mkdir -p mosquitto_data

# Start MQTT broker
echo "Starting MQTT broker..."
# Kill existing mosquitto if running
sudo pkill mosquitto 2>/dev/null || true
sleep 1
# Start with our configuration (all interfaces)
echo "Starting MQTT broker with config: mosquitto.conf"
sudo mosquitto -c mosquitto.conf -v &
sleep 3
echo "MQTT broker started"
# Check if MQTT broker is running
if pgrep mosquitto > /dev/null; then
    echo "MQTT broker is running"
    netstat -tlnp | grep 1883
else
    echo "Error: MQTT broker failed to start"
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

# Wait a moment for MQTT broker to start
sleep 3

# Start IoT Data Bridge (MQTT Only)
echo "Starting IoT Data Bridge (MQTT Only)..."

# Try python3 first, then python
if command -v python3 &> /dev/null; then
    echo "IoT Data Bridge is running... Press Ctrl+C to stop"
    python3 src/main_mqtt.py
elif command -v python &> /dev/null; then
    echo "IoT Data Bridge is running... Press Ctrl+C to stop"
    python src/main_mqtt.py
else
    echo "Error: Python not found. Please install Python 3.8 or higher."
    exit 1
fi

echo "IoT Data Bridge stopped. Cleaning up..."
# Stop MQTT broker
sudo pkill mosquitto 2>/dev/null || true
echo "All services stopped!"
