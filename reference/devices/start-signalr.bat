@echo off
REM Change to the directory where this script is located
cd /d "%~dp0"

echo ========================================
echo    IoT Data Bridge - Devices (SignalR)
echo ========================================
echo.

REM Check if .NET SDK is available (needed for SignalR Hub)
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

echo Checking Python dependencies...
echo Checking for required packages: signalrcore, aiomqtt, pyyaml, structlog...

REM Check each required package
set MISSING_PACKAGES=0
pip show signalrcore >nul 2>&1
if %ERRORLEVEL% neq 0 set MISSING_PACKAGES=1

pip show aiomqtt >nul 2>&1
if %ERRORLEVEL% neq 0 set MISSING_PACKAGES=1

pip show pyyaml >nul 2>&1
if %ERRORLEVEL% neq 0 set MISSING_PACKAGES=1

pip show structlog >nul 2>&1
if %ERRORLEVEL% neq 0 set MISSING_PACKAGES=1

if %MISSING_PACKAGES%==1 (
    echo Installing missing dependencies...
    pip install -r requirements.txt
    if %ERRORLEVEL% neq 0 (
        echo Error: Failed to install Python dependencies
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
echo Starting IoT Device (SignalR)...
echo.

echo Usage Examples:
echo    VM-A:     python signalr_device.py VM-A
echo    VM-B:     python signalr_device.py VM-B
echo    Custom:   python signalr_device.py MyDevice 192.168.1.100 5000
echo.

set /p DEVICE_ID="Enter Device ID (default: VM-A): "
if "%DEVICE_ID%"=="" set DEVICE_ID=VM-A

set /p SIGNALR_HOST="Enter SignalR hub host (default: localhost): "
if "%SIGNALR_HOST%"=="" set SIGNALR_HOST=localhost

set /p SIGNALR_PORT="Enter SignalR hub port (default: 5000): "
if "%SIGNALR_PORT%"=="" set SIGNALR_PORT=5000

echo.
echo Starting Device: %DEVICE_ID% with SignalR: %SIGNALR_HOST%:%SIGNALR_PORT%
echo.

python signalr_device.py %DEVICE_ID% %SIGNALR_HOST% %SIGNALR_PORT%

echo.
echo Device stopped.
pause
