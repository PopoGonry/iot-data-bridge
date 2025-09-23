@echo off
REM IoT Data Bridge Middleware Server Start Script (MQTT Only)

REM Change to the directory where this script is located
cd /d "%~dp0"

echo ========================================
echo    IoT Data Bridge - Middleware (MQTT Only)
echo ========================================
echo

REM Check if Python is available
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.11+ and try again
    pause
    exit /b 1
)

REM Check if requirements are installed
echo Checking Python dependencies...
echo Checking for required packages: aiomqtt, pydantic, structlog, pyyaml...

REM Check each required package
set MISSING_PACKAGES=0
pip show aiomqtt >nul 2>&1
if %ERRORLEVEL% neq 0 set MISSING_PACKAGES=1

pip show pydantic >nul 2>&1
if %ERRORLEVEL% neq 0 set MISSING_PACKAGES=1

pip show structlog >nul 2>&1
if %ERRORLEVEL% neq 0 set MISSING_PACKAGES=1

pip show pyyaml >nul 2>&1
if %ERRORLEVEL% neq 0 set MISSING_PACKAGES=1

if %MISSING_PACKAGES%==1 (
    echo Installing missing dependencies...
    pip install -r requirements.txt
    if %ERRORLEVEL% neq 0 (
        echo Error: Failed to install dependencies
        echo Please check your Python environment and internet connection
        pause
        exit /b 1
    )
    echo Dependencies installed successfully!
) else (
    echo All required dependencies are already installed.
)

echo Starting IoT Data Bridge Middleware Server (MQTT Only)...

REM Create logs directory
if not exist logs mkdir logs

REM Create mosquitto_data directory for MQTT broker persistence
if not exist mosquitto_data mkdir mosquitto_data

REM Start MQTT broker
echo Starting MQTT broker...
start /B mosquitto -c mosquitto.conf

REM Wait a moment for MQTT broker to start
timeout /t 3 /nobreak > nul

REM Start IoT Data Bridge (MQTT Only)
echo Starting IoT Data Bridge (MQTT Only)...
python src/main.py --config config/app-mqtt.yaml

echo All services started!
pause
