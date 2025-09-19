#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "   IoT Data Bridge - Devices (SignalR)"
echo "========================================"
echo

# Check if .NET SDK is available (needed for SignalR Hub)
echo "Checking .NET SDK..."
if ! command -v dotnet &> /dev/null; then
    echo ".NET SDK not found. Installing .NET SDK..."
    
    # Detect OS
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Ubuntu/Debian
        if command -v apt-get &> /dev/null; then
            echo "Installing .NET SDK for Ubuntu/Debian..."
            wget https://packages.microsoft.com/config/ubuntu/22.04/packages-microsoft-prod.deb -O packages-microsoft-prod.deb
            sudo dpkg -i packages-microsoft-prod.deb
            rm packages-microsoft-prod.deb
            sudo apt-get update
            sudo apt-get install -y dotnet-sdk-8.0
        # CentOS/RHEL
        elif command -v yum &> /dev/null; then
            echo "Installing .NET SDK for CentOS/RHEL..."
            sudo rpm -Uvh https://packages.microsoft.com/config/centos/7/packages-microsoft-prod.rpm
            sudo yum install -y dotnet-sdk-8.0
        else
            echo "Error: Unsupported Linux distribution. Please install .NET SDK manually."
            echo "Visit: https://dotnet.microsoft.com/download"
            exit 1
        fi
    # macOS
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "Installing .NET SDK for macOS..."
        if command -v brew &> /dev/null; then
            brew install --cask dotnet-sdk
        else
            echo "Error: Homebrew not found. Please install .NET SDK manually."
            echo "Visit: https://dotnet.microsoft.com/download"
            exit 1
        fi
    else
        echo "Error: Unsupported operating system. Please install .NET SDK manually."
        echo "Visit: https://dotnet.microsoft.com/download"
        exit 1
    fi
    
    if [ $? -ne 0 ]; then
        echo "Error: Failed to install .NET SDK"
        exit 1
    fi
    
    echo ".NET SDK installed successfully!"
fi

echo "Checking Python dependencies..."
python3 -c "import signalrcore" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing Python dependencies..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "Error: Failed to install Python dependencies"
        exit 1
    fi
fi

echo
echo "Starting IoT Device (SignalR)..."
echo

echo "Usage Examples:"
echo "   VM-A:     python3 signalr_device.py VM-A"
echo "   VM-B:     python3 signalr_device.py VM-B"
echo "   Custom:   python3 signalr_device.py MyDevice 192.168.1.100 5000"
echo

# Get device ID from user
read -p "Enter Device ID (default: VM-A): " DEVICE_ID
DEVICE_ID=${DEVICE_ID:-VM-A}

read -p "Enter SignalR hub host (default: localhost): " SIGNALR_HOST
SIGNALR_HOST=${SIGNALR_HOST:-localhost}

read -p "Enter SignalR hub port (default: 5000): " SIGNALR_PORT
SIGNALR_PORT=${SIGNALR_PORT:-5000}

echo
echo "Starting Device: $DEVICE_ID with SignalR: $SIGNALR_HOST:$SIGNALR_PORT"
echo

# Start the device (group name will be same as device ID)
python3 signalr_device.py $DEVICE_ID $SIGNALR_HOST $SIGNALR_PORT

echo
