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
echo Checking for required packages: signalrcore, pydantic, structlog, pyyaml...

REM Check each required package
set MISSING_PACKAGES=0
pip show signalrcore >nul 2>&1
if %ERRORLEVEL% neq 0 set MISSING_PACKAGES=1

pip show pydantic >nul 2>&1
if %ERRORLEVEL% neq 0 set MISSING_PACKAGES=1

pip show structlog >nul 2>&1
if %ERRORLEVEL% neq 0 set MISSING_PACKAGES=1

pip show pyyaml >nul 2>&1
if %ERRORLEVEL% neq 0 set MISSING_PACKAGES=1

if %MISSING_PACKAGES%==1 (
    echo Installing missing dependencies...
    echo Using requirements-signalr.txt for SignalR-specific dependencies...
    pip install -r requirements-signalr.txt
    if %ERRORLEVEL% neq 0 (
        echo Error: Failed to install dependencies from requirements-signalr.txt
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
echo Starting IoT Data Bridge Middleware (SignalR)...
echo.

REM Start the middleware
python src/main_signalr.py

echo.
echo Middleware stopped.
pause
