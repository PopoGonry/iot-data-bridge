#!/bin/bash
# IoT Data Bridge Stop Script

# Stop IoT Data Bridge
echo "Stopping IoT Data Bridge..."
pkill -f "python src/main.py"

# Stop SignalR Hub
echo "Stopping SignalR Hub..."
pkill -f "dotnet run"

# Stop MQTT broker
echo "Stopping MQTT broker..."
pkill -f "mosquitto"

echo "All services stopped"
