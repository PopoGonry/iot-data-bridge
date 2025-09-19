#!/bin/bash

echo "========================================"
echo "   IoT Data Bridge - Data Sources (SignalR)"
echo "========================================"
echo

echo "Checking dependencies..."
python3 -c "import signalrcore" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "Error: Failed to install dependencies"
        exit 1
    fi
fi

echo
echo "Starting Data Publisher (SignalR)..."
echo

python3 signalr_publisher.py "$@"

echo
echo "Data Publisher stopped."
