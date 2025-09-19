@echo off
REM IoT Data Bridge Middleware Server Start Script

echo Starting IoT Data Bridge Middleware Server...

REM Create logs directory
if not exist logs mkdir logs

REM Start MQTT broker
echo Starting MQTT broker...
start /B mosquitto -c mosquitto.conf

REM Start SignalR Hub
echo Starting SignalR Hub...
cd signalr_hub
start /B dotnet run
cd ..

REM Wait a moment for services to start
timeout /t 3 /nobreak > nul

REM Start IoT Data Bridge
echo Starting IoT Data Bridge...
python src/main.py --config config/app-multi-vm.yaml

echo All services started!
pause
