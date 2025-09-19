@echo off
REM Change to the directory where this script is located
cd /d "%~dp0"

echo ========================================
echo    IoT Data Bridge - Data Sources (SignalR)
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
echo Starting Data Publisher (SignalR)...
echo.

echo Usage Examples:
echo    Default:  python signalr_publisher.py
echo    Custom:   python signalr_publisher.py 192.168.1.100 5000
echo.

set /p SIGNALR_HOST="Enter SignalR hub host (default: localhost): "
if "%SIGNALR_HOST%"=="" set SIGNALR_HOST=localhost

set /p SIGNALR_PORT="Enter SignalR hub port (default: 5000): "
if "%SIGNALR_PORT%"=="" set SIGNALR_PORT=5000

echo.
echo Starting Data Publisher with SignalR: %SIGNALR_HOST%:%SIGNALR_PORT%
echo.

python signalr_publisher.py %SIGNALR_HOST% %SIGNALR_PORT%

echo.
echo Data Publisher stopped.
pause
