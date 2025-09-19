#!/bin/bash
# Data Source Installation Script

echo "Installing Data Source..."

# Check Python availability
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    PIP_CMD="pip3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
    PIP_CMD="pip"
else
    echo "Error: Python not found. Please install Python 3.7+"
    exit 1
fi

echo "Using Python: $PYTHON_CMD"

# Create virtual environment
echo "Creating virtual environment..."
$PYTHON_CMD -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
$PIP_CMD install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
$PIP_CMD install -r requirements.txt

echo "✅ Installation completed!"
echo ""
echo "To activate virtual environment:"
echo "  source venv/bin/activate"
echo ""
echo "To run data source:"
echo "  ./start.sh <broker_ip> [broker_port]"
