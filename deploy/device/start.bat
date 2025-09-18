@echo off
REM IoT Device Start Script

echo Starting IoT Device...

REM Check if device ID is provided
if "%1"=="" (
    echo Usage: start.bat ^<device_id^> [config_file]
    echo Example: start.bat VM-A
    echo Example: start.bat VM-A device_config.yaml
    pause
    exit /b 1
)

set DEVICE_ID=%1
set CONFIG_FILE=%2
if "%CONFIG_FILE%"=="" set CONFIG_FILE=device_config.yaml

echo Starting device: %DEVICE_ID%
echo Config file: %CONFIG_FILE%

REM Start device
python device.py %DEVICE_ID% %CONFIG_FILE%

pause
