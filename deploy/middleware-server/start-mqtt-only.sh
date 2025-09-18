#!/bin/bash
# IoT Data Bridge Middleware Server Start Script (MQTT Only)

echo "Starting IoT Data Bridge Middleware Server (MQTT Only)..."

# Create logs directory
mkdir -p logs

# Start MQTT broker
echo "Starting MQTT broker..."
mosquitto -c mosquitto.conf -d

# Wait a moment for MQTT broker to start
sleep 3

# Start IoT Data Bridge (MQTT Only)
echo "Starting IoT Data Bridge (MQTT Only)..."

# Try python3 first, then python
if command -v python3 &> /dev/null; then
    python3 src/main.py --config config/app-mqtt.yaml
elif command -v python &> /dev/null; then
    python src/main.py --config config/app-mqtt.yaml
else
    echo "Error: Python not found. Please install Python 3.8 or higher."
    exit 1
fi

echo "All services started!"
