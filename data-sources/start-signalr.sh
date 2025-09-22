#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "   IoT Data Bridge - Data Sources (SignalR)"
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
echo "Checking for required packages: signalrcore, aiomqtt, pyyaml..."

# Check each required package
MISSING_PACKAGES=0
if ! python3 -c "import signalrcore" &> /dev/null; then
    MISSING_PACKAGES=1
fi

if ! python3 -c "import aiomqtt" &> /dev/null; then
    MISSING_PACKAGES=1
fi

if ! python3 -c "import yaml" &> /dev/null; then
    MISSING_PACKAGES=1
fi

if [ $MISSING_PACKAGES -eq 1 ]; then
    echo "Installing missing dependencies..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "Error: Failed to install Python dependencies"
        echo "Please check your Python environment and internet connection"
        echo "You may need to run: pip3 install --upgrade pip"
        exit 1
    fi
    echo "Dependencies installed successfully!"
else
    echo "All required dependencies are already installed."
fi

echo
echo "Starting IoT Data Sources (SignalR)..."
echo

echo "Usage Examples:"
echo "   Default:  python3 signalr_publisher.py"
echo "   Custom:   python3 signalr_publisher.py 192.168.1.100 5000"
echo

# Get SignalR hub host and port from user
read -p "Enter SignalR hub host (default: localhost): " SIGNALR_HOST
SIGNALR_HOST=${SIGNALR_HOST:-localhost}

read -p "Enter SignalR hub port (default: 5000): " SIGNALR_PORT
SIGNALR_PORT=${SIGNALR_PORT:-5000}

echo
echo "Starting Data Publisher with SignalR: $SIGNALR_HOST:$SIGNALR_PORT"
echo

# Start the publisher (group name will be iot_clients by default)
python3 signalr_publisher.py $SIGNALR_HOST $SIGNALR_PORT

echo
