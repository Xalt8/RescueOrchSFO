@echo off
setlocal enabledelayedexpansion

set "ROOT=%~dp0"

:: Check for port conflicts and kill existing processes
echo Checking for port conflicts...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo Port 8000 is in use. Stopping existing process...
    taskkill /PID %%a /F >nul 2>&1
    timeout /t 2 /nobreak >nul
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5173" ^| findstr "LISTENING"') do (
    echo Port 5173 is in use. Stopping existing process...
    taskkill /PID %%a /F >nul 2>&1
    timeout /t 1 /nobreak >nul
)

:: Backend setup
cd /d "%ROOT%backend"
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

echo Installing backend dependencies...
pip install -q -r requirements.txt
if errorlevel 1 (
    echo Error: Failed to install backend dependencies.
    pause
    exit /b 1
)

echo Starting backend on http://localhost:8000
start "Rescue Command Center - Backend" cmd /k "venv\Scripts\activate.bat && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

:: Frontend setup
cd /d "%ROOT%frontend"
if not exist "node_modules" (
    echo Installing frontend dependencies...
    call npm install
    if errorlevel 1 (
        echo Error: npm not found. Please install Node.js.
        pause
        exit /b 1
    )
)

echo Starting frontend on http://localhost:5173
start "Rescue Command Center - Frontend" cmd /k "npm run dev"

echo.
echo Rescue Command Center running:
echo   Backend:  http://localhost:8000 (docs: /docs)
echo   Frontend: http://localhost:5173
echo.
echo Both services are running in separate windows.
echo Close the windows or press Ctrl+C in each window to stop.
echo.
pause
