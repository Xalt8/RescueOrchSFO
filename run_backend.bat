@echo off
setlocal

cd /d "%~dp0backend"

if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo Error: Python not found. Please install Python 3.8 or higher.
        pause
        exit /b 1
    )
)

call venv\Scripts\activate.bat
if errorlevel 1 (
    echo Error: Failed to activate virtual environment.
    pause
    exit /b 1
)

echo Installing dependencies...
pip install -q -r requirements.txt
if errorlevel 1 (
    echo Error: Failed to install dependencies.
    pause
    exit /b 1
)

echo Starting backend on http://localhost:8000
echo API docs: http://localhost:8000/docs
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

pause
