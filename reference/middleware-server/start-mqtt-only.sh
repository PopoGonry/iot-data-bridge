#!/bin/bash
# IoT Data Bridge Middleware Server Start Script (MQTT Only)

# Change to script directory
cd "$(dirname "$0")"

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
