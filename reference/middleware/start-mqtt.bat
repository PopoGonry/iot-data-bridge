@echo off
REM Middleware Start Script for Windows - MQTT Only

REM Change to the directory where this script is located
cd /d "%~dp0"

echo ========================================
echo    IoT Data Bridge - Middleware (MQTT)
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
    echo Using requirements-mqtt.txt for MQTT-specific dependencies...
    pip install -r requirements-mqtt.txt
    if %ERRORLEVEL% neq 0 (
        echo Error: Failed to install dependencies from requirements-mqtt.txt
        echo Trying fallback to requirements.txt...
        pip install -r requirements.txt
        if %ERRORLEVEL% neq 0 (
            echo Error: Failed to install dependencies
            echo Please check your Python environment and internet connection
            pause
            exit /b 1
        )
    )
    echo Dependencies installed successfully!
) else (
    echo All required dependencies are already installed.
)

echo.
echo Starting IoT Data Bridge Middleware (MQTT)...
echo.

REM Start the middleware
python src/main_mqtt.py
