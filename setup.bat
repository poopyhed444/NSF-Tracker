@echo off
REM Setup script for NIH/NSF At-Risk Labs Tracker

echo Setting up NIH/NSF At-Risk Labs Tracker...

REM Backend setup
echo Setting up backend...
cd backend

REM Create virtual environment
echo Creating virtual environment...
python -m venv venv

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing Python dependencies...
pip install -r requirements.txt

echo Backend setup complete!

REM Go back to root directory
cd ..

echo Setup complete! To run the application:
echo 1. Backend: cd backend ^&^& python main.py
echo 2. Frontend: cd frontend ^&^& npm start

pause
