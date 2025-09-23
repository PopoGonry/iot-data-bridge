#!/bin/bash
# IoT Device Start Script

# Change to script directory
cd "$(dirname "$0")"

echo "Starting IoT Device..."
echo "Working directory: $(pwd)"

# Check if device ID is provided
if [ $# -eq 0 ]; then
    echo "Usage: ./start.sh <device_id> [config_file]"
    echo "Example: ./start.sh VM-A"
    echo "Example: ./start.sh VM-A device_config.yaml"
    exit 1
fi

DEVICE_ID=$1
CONFIG_FILE=${2:-"device_config.yaml"}

echo "Starting device: $DEVICE_ID"
echo "Config file: $CONFIG_FILE"

# Try to activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
    echo "Virtual environment activated: $(which python)"
elif [ -f ".venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
    echo "Virtual environment activated: $(which python)"
else
    echo "Warning: No virtual environment found. Using system Python."
fi

# Check Python availability
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "Error: Python not found. Please install Python 3.7+"
    exit 1
fi

echo "Using Python: $PYTHON_CMD"

# Check if requirements are installed
echo "Checking dependencies..."
echo "Checking for required packages: aiomqtt, signalrcore, pyyaml, structlog..."

# Check each required package
MISSING_PACKAGES=0
if ! $PYTHON_CMD -c "import aiomqtt" &> /dev/null; then
    MISSING_PACKAGES=1
fi

if ! $PYTHON_CMD -c "import signalrcore" &> /dev/null; then
    MISSING_PACKAGES=1
fi

if ! $PYTHON_CMD -c "import yaml" &> /dev/null; then
    MISSING_PACKAGES=1
fi

if ! $PYTHON_CMD -c "import structlog" &> /dev/null; then
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

# Check if device.py exists
if [ ! -f "device.py" ]; then
    echo "Error: device.py not found in current directory"
    exit 1
fi

echo "Starting device..."
echo "Command: $PYTHON_CMD device.py $DEVICE_ID $CONFIG_FILE"
$PYTHON_CMD device.py $DEVICE_ID $CONFIG_FILE
