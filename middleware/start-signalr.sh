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

# Check if SignalR Hub is already running
if netstat -tlnp 2>/dev/null | grep -q ":5000 "; then
    echo "SignalR Hub is already running on port 5000"
else
    echo "SignalR Hub is not running. Starting automatically..."
    
    # Create logs directory if it doesn't exist
    mkdir -p logs
    
    # Function to cleanup on exit
    cleanup() {
        echo
        echo "Stopping services..."
        
        # Stop SignalR Hub
        if [ ! -z "$HUB_PID" ] && kill -0 $HUB_PID 2>/dev/null; then
            echo "Stopping SignalR Hub (PID: $HUB_PID)..."
            kill $HUB_PID
            wait $HUB_PID 2>/dev/null
        fi
        
        echo "All services stopped."
        exit 0
    }
    
    # Set up signal handlers
    trap cleanup SIGINT SIGTERM
    
    # Start SignalR Hub in background
    echo "Starting SignalR Hub..."
    cd signalr_hub
    nohup dotnet run > ../logs/signalr_hub.log 2>&1 &
    HUB_PID=$!
    cd ..
    
    # Wait for SignalR Hub to start
    echo "Waiting for SignalR Hub to start..."
    sleep 3
    
    # Check if SignalR Hub is running and listening on port 5000
    for i in {1..15}; do
        if netstat -tlnp 2>/dev/null | grep -q ":5000 "; then
            echo "SignalR Hub started successfully (PID: $HUB_PID)"
            break
        elif ! kill -0 $HUB_PID 2>/dev/null; then
            echo "Error: SignalR Hub failed to start"
            echo "Check logs/signalr_hub.log for details:"
            if [ -f logs/signalr_hub.log ]; then
                tail -20 logs/signalr_hub.log
            fi
            exit 1
        else
            echo "Waiting for SignalR Hub to be ready... ($i/15)"
            sleep 1
        fi
    done
    
    # Final check
    if ! netstat -tlnp 2>/dev/null | grep -q ":5000 "; then
        echo "Error: SignalR Hub is not listening on port 5000"
        echo "Check logs/signalr_hub.log for details:"
        if [ -f logs/signalr_hub.log ]; then
            tail -20 logs/signalr_hub.log
        fi
        kill $HUB_PID 2>/dev/null
        exit 1
    fi
fi

# Start the middleware
echo "Starting IoT Data Bridge Middleware..."
python3 src/main_signalr.py

# Cleanup will be handled by the signal handler if SignalR Hub was started by this script
