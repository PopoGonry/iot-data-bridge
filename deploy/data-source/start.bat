@echo off
REM Data Source Start Script

echo Starting Data Source...

REM Check if broker IP is provided
if "%1"=="" (
    echo Usage: start.bat ^<broker_ip^> [broker_port]
    echo Example: start.bat 192.168.1.100 1883
    pause
    exit /b 1
)

set BROKER_IP=%1
set BROKER_PORT=%2
if "%BROKER_PORT%"=="" set BROKER_PORT=1883

echo Connecting to MQTT broker at %BROKER_IP%:%BROKER_PORT%

REM Start data publisher
python test_mqtt_publisher-multi-vm.py %BROKER_IP% %BROKER_PORT%

pause
