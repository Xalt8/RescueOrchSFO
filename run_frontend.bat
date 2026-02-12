@echo off
setlocal

cd /d "%~dp0frontend"

if not exist "node_modules" (
    echo Installing dependencies...
    call npm install
    if errorlevel 1 (
        echo Error: npm not found. Please install Node.js.
        pause
        exit /b 1
    )
)

echo Starting frontend on http://localhost:5173
call npm run dev

pause
