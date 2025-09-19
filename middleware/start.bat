@echo off
REM Middleware Start Script for Windows

echo ========================================
echo    IoT Data Bridge - Middleware
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ❌ Error: Python is not installed or not in PATH
    echo 💡 Please install Python 3.11+ and try again
    pause
    exit /b 1
)

REM Check if requirements are installed
echo 📦 Checking dependencies...
pip show aiomqtt >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo 📥 Installing dependencies...
    pip install -r requirements.txt
    if %ERRORLEVEL% neq 0 (
        echo ❌ Error: Failed to install dependencies
        pause
        exit /b 1
    )
)

echo.
echo 🚀 Starting IoT Data Bridge Middleware...
echo.

REM Start the middleware
python src/main.py

echo.
echo 👋 Middleware stopped.
pause
