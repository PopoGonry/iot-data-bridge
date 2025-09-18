@echo off
REM Data Source Start Script

REM Change to script directory
cd /d "%~dp0"

echo Starting Data Source...
echo Working directory: %CD%

REM Check if broker IP is provided
if "%1"=="" (
    echo Usage: start.bat ^<broker_ip^> [broker_port]
    echo Example: start.bat 192.168.1.100 1883
    pause
    exit /b 1
)

set BROKER_IP=%1
set BROKER_PORT=%2
if "%BROKER_PORT%"=="" set BROKER_PORT=1883

echo Connecting to MQTT broker at %BROKER_IP%:%BROKER_PORT%

REM Try to activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
    echo Virtual environment activated
) else if exist ".venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
    echo Virtual environment activated
) else (
    echo Warning: No virtual environment found. Using system Python.
)

REM Check Python availability
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python not found. Please install Python 3.7+
    pause
    exit /b 1
)

echo Using Python: 
python --version

REM Check if requirements are installed
echo Checking dependencies...
python -c "import aiomqtt" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing dependencies...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo Error: Failed to install dependencies
        pause
        exit /b 1
    )
)

echo Starting data publisher...
python test_mqtt_publisher-multi-vm.py %BROKER_IP% %BROKER_PORT%

pause
