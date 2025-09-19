@echo off
echo ========================================
echo    IoT Data Bridge - Data Sources (SignalR)
echo ========================================
echo.

echo Checking dependencies...
python -c "import signalrcore" 2>nul
if %errorlevel% neq 0 (
    echo Installing dependencies...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo Error: Failed to install dependencies
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
