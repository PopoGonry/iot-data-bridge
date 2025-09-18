@echo off
REM IoT Data Bridge Stop Script for Windows

REM Stop IoT Data Bridge
echo Stopping IoT Data Bridge...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq IoT Data Bridge*" 2>nul

REM Stop SignalR Hub
echo Stopping SignalR Hub...
taskkill /F /IM dotnet.exe 2>nul

REM Stop MQTT broker
echo Stopping MQTT broker...
taskkill /F /IM mosquitto.exe 2>nul

echo All services stopped

