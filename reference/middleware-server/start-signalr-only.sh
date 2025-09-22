#!/bin/bash
# IoT Data Bridge Middleware Server Start Script (SignalR Only)

echo "========================================"
echo "   IoT Data Bridge - Middleware (SignalR Only)"
echo "========================================"
echo

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python3 is not installed or not in PATH"
    echo "Please install Python 3.11+ and try again"
    exit 1
fi

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
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "Error: Failed to install dependencies"
        echo "Please check your Python environment and internet connection"
        echo "You may need to run: pip3 install --upgrade pip"
        exit 1
    fi
    echo "Dependencies installed successfully!"
else
    echo "All required dependencies are already installed."
fi

# Start SignalR Hub
echo "Starting SignalR Hub..."
if command -v dotnet &> /dev/null; then
    cd signalr_hub
    dotnet run &
    HUB_PID=$!
    cd ..
    echo "SignalR Hub started (PID: $HUB_PID)"
    
    # Wait a moment for SignalR Hub to start
    sleep 5
    
    # Check if SignalR Hub is running
    if ! kill -0 $HUB_PID 2>/dev/null; then
        echo "Error: SignalR Hub failed to start"
        exit 1
    fi
    
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
    
    echo
    echo "Stopping services..."
    
    # Stop SignalR Hub
    if kill -0 $HUB_PID 2>/dev/null; then
        echo "Stopping SignalR Hub (PID: $HUB_PID)..."
        kill $HUB_PID
        wait $HUB_PID 2>/dev/null
    fi
    
    echo "All services stopped."
else
    echo "Error: dotnet not found. Please install .NET SDK:"
    echo "https://dotnet.microsoft.com/download"
    exit 1
fi
