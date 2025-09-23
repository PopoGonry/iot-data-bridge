#!/bin/bash
# Middleware Start Script for Linux/macOS - SignalR Only

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "   IoT Data Bridge - Middleware (SignalR)"
echo "========================================"
echo

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python3 is not installed or not in PATH"
    echo "Please install Python 3.11+ and try again"
    exit 1
fi

# Check if .NET SDK is available
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

# Check if requirements are installed
echo "Checking Python dependencies..."
echo "Checking for required packages: signalrcore, pydantic, structlog, pyyaml..."

# Check each required package
MISSING_PACKAGES=0
if ! python3 -c "import signalrcore" &> /dev/null; then
    MISSING_PACKAGES=1
fi

if ! python3 -c "import pydantic" &> /dev/null; then
    MISSING_PACKAGES=1
fi

if ! python3 -c "import structlog" &> /dev/null; then
    MISSING_PACKAGES=1
fi

if ! python3 -c "import yaml" &> /dev/null; then
    MISSING_PACKAGES=1
fi

if [ $MISSING_PACKAGES -eq 1 ]; then
    echo "Installing missing dependencies..."
    echo "Using requirements-signalr.txt for SignalR-specific dependencies..."
    pip3 install -r requirements-signalr.txt
    if [ $? -ne 0 ]; then
        echo "Error: Failed to install dependencies from requirements-signalr.txt"
        echo "Trying fallback to requirements.txt..."
        pip3 install -r requirements.txt
        if [ $? -ne 0 ]; then
            echo "Error: Failed to install dependencies"
            echo "Please check your Python environment and internet connection"
            echo "You may need to run: pip3 install --upgrade pip"
            exit 1
        fi
    fi
    echo "Dependencies installed successfully!"
else
    echo "All required dependencies are already installed."
fi

echo
echo "Starting IoT Data Bridge Middleware (SignalR)..."
echo

# Check if SignalR server is running
echo "Checking if SignalR server is running..."

# Kill any existing dotnet processes to avoid port conflicts
echo "Stopping any existing SignalR servers..."
pkill -f "dotnet.*signalr_hub" 2>/dev/null || true
pkill -f "dotnet run" 2>/dev/null || true

# Wait a moment for processes to stop
sleep 2

# Check if port 5000 is still in use
if netstat -tlnp 2>/dev/null | grep -q ":5000 "; then
    echo "Port 5000 is still in use. Force killing processes..."
    sudo lsof -ti:5000 | xargs sudo kill -9 2>/dev/null || true
    sleep 2
fi

# Now start SignalR server
echo "Starting SignalR server..."
cd signalr_hub
nohup dotnet run > ../signalr_server.log 2>&1 &
SIGNALR_PID=$!
cd ..

# Wait for server to start
echo "Waiting for SignalR server to start..."
for i in {1..10}; do
    if curl -s http://localhost:5000/ > /dev/null 2>&1; then
        echo "SignalR server started successfully!"
        break
    fi
    echo "Attempt $i/10: Waiting for server..."
    sleep 2
done

# Check if server started successfully
if ! curl -s http://localhost:5000/ > /dev/null 2>&1; then
    echo "Error: Failed to start SignalR server"
    echo "Check signalr_server.log for details"
    exit 1
fi

# Start the middleware
python3 src/main_signalr.py

echo
echo "Middleware stopped."
