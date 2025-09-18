#!/bin/bash
# IoT Data Bridge Start Script

# Create logs directory if it doesn't exist
mkdir -p logs

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Start MQTT broker (Mosquitto)
echo "Starting MQTT broker..."
mosquitto -c mosquitto.conf -d
echo "MQTT broker started on localhost:1883"

# Start SignalR Hub (if .NET is available)
if command -v dotnet &> /dev/null; then
    echo "Starting SignalR Hub..."
    cd signalr_hub
    dotnet run &
    cd ..
    echo "SignalR Hub started on localhost:5000"
else
    echo "Warning: .NET not found, SignalR Hub not started"
fi

# Wait a moment for services to start
sleep 2

# Start the IoT Data Bridge application
echo "Starting IoT Data Bridge..."
python src/main.py
