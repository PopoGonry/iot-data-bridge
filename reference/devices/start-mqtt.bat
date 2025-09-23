@echo off
REM Devices Start Script for Windows

REM Change to the directory where this script is located
cd /d "%~dp0"

echo ========================================
echo    IoT Data Bridge - Devices
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
echo Checking for required packages: aiomqtt, signalrcore, pyyaml, structlog...

REM Check each required package
set MISSING_PACKAGES=0
pip show aiomqtt >nul 2>&1
if %ERRORLEVEL% neq 0 set MISSING_PACKAGES=1

pip show signalrcore >nul 2>&1
if %ERRORLEVEL% neq 0 set MISSING_PACKAGES=1

pip show pyyaml >nul 2>&1
if %ERRORLEVEL% neq 0 set MISSING_PACKAGES=1

pip show structlog >nul 2>&1
if %ERRORLEVEL% neq 0 set MISSING_PACKAGES=1

if %MISSING_PACKAGES%==1 (
    echo Installing missing dependencies...
    pip install -r requirements.txt
    if %ERRORLEVEL% neq 0 (
        echo Error: Failed to install dependencies
        echo Please check your Python environment and internet connection
        echo You may need to run: pip install --upgrade pip
        pause
        exit /b 1
    )
    echo Dependencies installed successfully!
) else (
    echo All required dependencies are already installed.
)

echo.
echo Starting IoT Device...
echo.
echo Usage Examples:
echo    VM-A:     python device.py VM-A
echo    VM-B:     python device.py VM-B
echo    Custom:   python device.py MyDevice localhost 1883
echo.

REM Get device ID from user
set /p DEVICE_ID="Enter Device ID (default: VM-A): "
if "%DEVICE_ID%"=="" set DEVICE_ID=VM-A

set /p MQTT_HOST="Enter MQTT broker host (default: localhost): "
if "%MQTT_HOST%"=="" set MQTT_HOST=localhost

set /p MQTT_PORT="Enter MQTT broker port (default: 1883): "
if "%MQTT_PORT%"=="" set MQTT_PORT=1883

echo.
echo Starting Device: %DEVICE_ID% with broker: %MQTT_HOST%:%MQTT_PORT%
echo.

REM Start the device
python device.py %DEVICE_ID% %MQTT_HOST% %MQTT_PORT%

echo.
echo Device stopped.
pause
