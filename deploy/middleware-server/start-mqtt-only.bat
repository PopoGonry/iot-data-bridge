@echo off
REM IoT Data Bridge Middleware Server Start Script (MQTT Only)

echo Starting IoT Data Bridge Middleware Server (MQTT Only)...

REM Create logs directory
if not exist logs mkdir logs

REM Create mosquitto_data directory for MQTT broker persistence
if not exist mosquitto_data mkdir mosquitto_data

REM Start MQTT broker
echo Starting MQTT broker...
start /B mosquitto -c mosquitto.conf

REM Wait a moment for MQTT broker to start
timeout /t 3 /nobreak > nul

REM Start IoT Data Bridge (MQTT Only)
echo Starting IoT Data Bridge (MQTT Only)...
python src/main.py --config config/app-mqtt.yaml

echo All services started!
pause
