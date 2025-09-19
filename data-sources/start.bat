@echo off
REM Data Sources Start Script for Windows

REM Change to the directory where this script is located
cd /d "%~dp0"

echo ========================================
echo    IoT Data Bridge - Data Sources
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.11+ and try again
    pause
    exit /b 1
)

REM Check if requirements are installed
echo Checking dependencies...
pip show aiomqtt >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Installing dependencies...
    pip install -r requirements.txt
    if %ERRORLEVEL% neq 0 (
        echo Error: Failed to install dependencies
        pause
        exit /b 1
    )
)

echo.
echo Starting Data Publisher...
echo.
echo Usage Examples:
echo    Local:    python mqtt_publisher.py localhost 1883
echo    Remote:   python mqtt_publisher.py 192.168.1.100 1883
echo.

REM Get broker host from user
set /p BROKER_HOST="Enter MQTT broker host (default: localhost): "
if "%BROKER_HOST%"=="" set BROKER_HOST=localhost

set /p BROKER_PORT="Enter MQTT broker port (default: 1883): "
if "%BROKER_PORT%"=="" set BROKER_PORT=1883

echo.
echo Starting with broker: %BROKER_HOST%:%BROKER_PORT%
echo.

REM Start the publisher
python mqtt_publisher.py %BROKER_HOST% %BROKER_PORT%

echo.
echo Data Publisher stopped.
pause
