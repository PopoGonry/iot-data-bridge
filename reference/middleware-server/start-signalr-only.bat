@echo off
REM IoT Data Bridge Middleware Server Start Script (SignalR Only)

REM Change to the directory where this script is located
cd /d "%~dp0"

echo ========================================
echo    IoT Data Bridge - Middleware (SignalR Only)
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

echo Starting IoT Data Bridge Middleware Server (SignalR Only)...

REM Create logs directory
if not exist logs mkdir logs

REM Start SignalR Hub
echo Starting SignalR Hub...
cd signalr_hub
start /B dotnet run
cd ..

REM Wait a moment for SignalR Hub to start
timeout /t 5 /nobreak > nul

echo SignalR Hub started successfully

REM Start IoT Data Bridge (SignalR Only)
echo Starting IoT Data Bridge (SignalR Only)...
python src/main.py --config config/app-signalr.yaml

echo.
echo Middleware stopped.
echo.
echo Note: SignalR Hub is still running in the background.
echo To stop it, check Task Manager or run: taskkill /f /im dotnet.exe
pause
