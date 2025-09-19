#!/bin/bash
# Middleware Start Script for Linux/macOS

echo "========================================"
echo "   IoT Data Bridge - Middleware"
echo "========================================"
echo

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python3 is not installed or not in PATH"
    echo "💡 Please install Python 3.11+ and try again"
    exit 1
fi

# Check if requirements are installed
echo "📦 Checking dependencies..."
if ! python3 -c "import aiomqtt" &> /dev/null; then
    echo "📥 Installing dependencies..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ Error: Failed to install dependencies"
        exit 1
    fi
fi

echo
echo "🚀 Starting IoT Data Bridge Middleware..."
echo

# Start the middleware
python3 src/main.py

echo
echo "👋 Middleware stopped."
