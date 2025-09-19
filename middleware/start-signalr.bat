@echo off
REM Middleware Start Script for Windows - SignalR Only

REM Change to the directory where this script is located
cd /d "%~dp0"

echo ========================================
echo    IoT Data Bridge - Middleware (SignalR)
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

REM Check if .NET SDK is available
echo Checking .NET SDK...
dotnet --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo .NET SDK not found. Installing .NET SDK...
    echo.
    echo Please download and install .NET SDK from:
    echo https://dotnet.microsoft.com/download
    echo.
    echo After installation, please restart this script.
    pause
    exit /b 1
)

REM Check if requirements are installed
echo Checking Python dependencies...
pip show signalrcore >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Installing Python dependencies...
    pip install -r requirements.txt
    if %ERRORLEVEL% neq 0 (
        echo Error: Failed to install Python dependencies
        pause
        exit /b 1
    )
)

echo.
echo Starting IoT Data Bridge Middleware (SignalR)...
echo.

REM Start the middleware
python src/main_signalr.py

echo.
echo Middleware stopped.
pause
