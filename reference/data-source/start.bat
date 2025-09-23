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
echo Checking for required packages: aiomqtt, signalrcore, pyyaml...

REM Check each required package
set MISSING_PACKAGES=0
pip show aiomqtt >nul 2>&1
if %ERRORLEVEL% neq 0 set MISSING_PACKAGES=1

pip show signalrcore >nul 2>&1
if %ERRORLEVEL% neq 0 set MISSING_PACKAGES=1

pip show pyyaml >nul 2>&1
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

echo Starting data publisher...
python test_mqtt_publisher-multi-vm.py %BROKER_IP% %BROKER_PORT%

pause
