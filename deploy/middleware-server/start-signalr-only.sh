#!/bin/bash
# IoT Data Bridge Middleware Server Start Script (SignalR Only)

echo "Starting IoT Data Bridge Middleware Server (SignalR Only)..."

# Create logs directory
mkdir -p logs

# Start SignalR Hub
echo "Starting SignalR Hub..."
if command -v dotnet &> /dev/null; then
    cd signalr_hub
    dotnet run &
    cd ..
    echo "SignalR Hub started"
    
    # Wait a moment for SignalR Hub to start
    sleep 5
    
    # Start IoT Data Bridge (SignalR Only)
    echo "Starting IoT Data Bridge (SignalR Only)..."
    python src/main.py --config config/app-signalr.yaml
else
    echo "Error: dotnet not found. Please install .NET SDK:"
    echo "https://dotnet.microsoft.com/download"
    exit 1
fi

echo "All services started!"
