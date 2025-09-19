@echo off
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

python signalr_publisher.py %1 %2

echo.
echo Data Publisher stopped.
pause
