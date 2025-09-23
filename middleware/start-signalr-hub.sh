#!/bin/bash
# SignalR Hub Start Script

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "   IoT Data Bridge - SignalR Hub"
echo "========================================"
echo

# Check if .NET SDK is available
echo "Checking .NET SDK..."
if ! command -v dotnet &> /dev/null; then
    echo "Error: .NET SDK not found. Please install .NET SDK first."
    echo "Visit: https://dotnet.microsoft.com/download"
    exit 1
fi

echo ".NET SDK found: $(dotnet --version)"

# Check if signalr_hub directory exists
if [ ! -d "signalr_hub" ]; then
    echo "Error: signalr_hub directory not found"
    exit 1
fi

echo "Starting SignalR Hub..."
echo "Hub will be available at: http://localhost:5000"
echo "Press Ctrl+C to stop the hub"
echo

# Start the SignalR hub
cd signalr_hub
dotnet run
