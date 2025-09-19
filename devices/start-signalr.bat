@echo off
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
python -c "import signalrcore" 2>nul
if %errorlevel% neq 0 (
    echo Installing Python dependencies...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo Error: Failed to install Python dependencies
        pause
        exit /b 1
    )
)

echo.
echo Starting IoT Device (SignalR)...
echo.

echo Usage Examples:
echo    VM-A:     python signalr_device.py VM-A
echo    VM-B:     python signalr_device.py VM-B
echo    Custom:   python signalr_device.py MyDevice http://192.168.1.100:5000/hub MyGroup
echo.

set /p device_id="Enter Device ID (default: VM-A): "
if "%device_id%"=="" set device_id=VM-A

set /p signalr_url="Enter SignalR hub URL (default: http://localhost:5000/hub): "
if "%signalr_url%"=="" set signalr_url=http://localhost:5000/hub

set /p group_name="Enter Group name (default: %device_id%): "
if "%group_name%"=="" set group_name=%device_id%

echo.
echo Starting Device: %device_id% with SignalR: %signalr_url%
echo.

python signalr_device.py %device_id% %signalr_url% %group_name%

echo.
echo Device stopped.
pause
