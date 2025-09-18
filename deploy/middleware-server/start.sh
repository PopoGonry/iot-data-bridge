#!/bin/bash
# IoT Data Bridge Middleware Server Start Script

echo "IoT Data Bridge Middleware Server"
echo "================================="
echo "1. MQTT Only"
echo "2. SignalR Only"
echo "3. Exit"
echo ""

read -p "Select option (1-3): " choice

case $choice in
    1)
        echo "Starting MQTT Only mode..."
        ./start-mqtt-only.sh
        ;;
    2)
        echo "Starting SignalR Only mode..."
        ./start-signalr-only.sh
        ;;
    3)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo "Invalid option. Please select 1, 2, or 3."
        exit 1
        ;;
esac