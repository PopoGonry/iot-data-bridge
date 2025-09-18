#!/bin/bash
# IoT Data Bridge Middleware Server Start Script (SignalR Only)

echo "Starting IoT Data Bridge Middleware Server (SignalR Only)..."

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
    
    # Try python3 first, then python
    if command -v python3 &> /dev/null; then
        python3 src/main_signalr.py
    elif command -v python &> /dev/null; then
        python src/main_signalr.py
    else
        echo "Error: Python not found. Please install Python 3.8 or higher."
        exit 1
    fi
else
    echo "Error: dotnet not found. Please install .NET SDK:"
    echo "https://dotnet.microsoft.com/download"
    exit 1
fi

echo "All services started!"
