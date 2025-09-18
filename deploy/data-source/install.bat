@echo off
REM Data Source Installation Script

echo Installing Data Source...

REM Check Python availability
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python not found. Please install Python 3.7+
    pause
    exit /b 1
)

echo Using Python:
python --version

REM Create virtual environment
echo Creating virtual environment...
python -m venv venv

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

echo ✅ Installation completed!
echo.
echo To activate virtual environment:
echo   venv\Scripts\activate.bat
echo.
echo To run data source:
echo   start.bat ^<broker_ip^> [broker_port]

pause
