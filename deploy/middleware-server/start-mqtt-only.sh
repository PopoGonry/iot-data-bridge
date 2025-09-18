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
python src/main.py --config config/app-mqtt.yaml

echo "All services started!"
