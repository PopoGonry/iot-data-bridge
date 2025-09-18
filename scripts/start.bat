@echo off
REM IoT Data Bridge Start Script for Windows

REM Create logs directory if it doesn't exist
if not exist logs mkdir logs

REM Start MQTT broker (Mosquitto)
echo Starting MQTT broker...
start /B mosquitto -c mosquitto.conf
echo MQTT broker started on localhost:1883

REM Start SignalR Hub (if .NET is available)
where dotnet >nul 2>nul
if %ERRORLEVEL% == 0 (
    echo Starting SignalR Hub...
    cd signalr_hub
    start /B dotnet run
    cd ..
    echo SignalR Hub started on localhost:5000
) else (
    echo Warning: .NET not found, SignalR Hub not started
)

REM Wait a moment for services to start
timeout /t 2 /nobreak >nul

REM Start the IoT Data Bridge application
echo Starting IoT Data Bridge...
python src/main.py

