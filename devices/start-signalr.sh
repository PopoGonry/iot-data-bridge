#!/bin/bash

echo "========================================"
echo "   IoT Data Bridge - Devices (SignalR)"
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
echo "Starting IoT Device (SignalR)..."
echo

echo "Usage Examples:"
echo "   VM-A:     python3 signalr_device.py VM-A"
echo "   VM-B:     python3 signalr_device.py VM-B"
echo "   Custom:   python3 signalr_device.py MyDevice http://192.168.1.100:5000/hub MyGroup"
echo

read -p "Enter Device ID (default: VM-A): " device_id
device_id=${device_id:-VM-A}

read -p "Enter SignalR hub URL (default: http://localhost:5000/hub): " signalr_url
signalr_url=${signalr_url:-http://localhost:5000/hub}

read -p "Enter Group name (default: $device_id): " group_name
group_name=${group_name:-$device_id}

echo
echo "Starting Device: $device_id with SignalR: $signalr_url"
echo

python3 signalr_device.py "$device_id" "$signalr_url" "$group_name"

echo
echo "Device stopped."
