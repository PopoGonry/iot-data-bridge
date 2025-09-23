@echo off
REM IoT Device Start Script

REM Change to the directory where this script is located
cd /d "%~dp0"

echo ========================================
echo    IoT Data Bridge - Device
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

echo Starting IoT Device...

REM Check if device ID is provided
if "%1"=="" (
    echo Usage: start.bat ^<device_id^> [config_file]
    echo Example: start.bat VM-A
    echo Example: start.bat VM-A device_config.yaml
    pause
    exit /b 1
)

set DEVICE_ID=%1
set CONFIG_FILE=%2
if "%CONFIG_FILE%"=="" set CONFIG_FILE=device_config.yaml

echo Starting device: %DEVICE_ID%
echo Config file: %CONFIG_FILE%

REM Start device
python device.py %DEVICE_ID% %CONFIG_FILE%

pause
