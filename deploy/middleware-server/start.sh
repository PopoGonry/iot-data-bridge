#!/bin/bash
# IoT Data Bridge Middleware Server Start Script

echo "Starting IoT Data Bridge Middleware Server..."

# Create logs directory
mkdir -p logs

# Start MQTT broker
echo "Starting MQTT broker..."
mosquitto -c mosquitto.conf -d

# Start SignalR Hub
echo "Starting SignalR Hub..."
cd signalr_hub
dotnet run &
cd ..

# Wait a moment for services to start
sleep 3

# Start IoT Data Bridge
echo "Starting IoT Data Bridge..."
python src/main.py --config config/app-multi-vm.yaml

echo "All services started!"
