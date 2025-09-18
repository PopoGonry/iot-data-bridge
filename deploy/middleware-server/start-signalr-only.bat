@echo off
REM IoT Data Bridge Middleware Server Start Script (SignalR Only)

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

REM Start IoT Data Bridge (SignalR Only)
echo Starting IoT Data Bridge (SignalR Only)...
python src/main.py --config config/app-signalr.yaml

echo All services started!
pause
