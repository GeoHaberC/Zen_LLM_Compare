@echo off
title Zen LLM Compare

echo Stopping any old servers on port 8123...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8123 "') do (
    taskkill /PID %%a /F >nul 2>&1
)
timeout /t 1 /nobreak >nul

echo Starting backend on port 8123...
start "Backend" /MIN python "%~dp0comparator_backend.py" 8123

timeout /t 2 /nobreak >nul

echo Opening browser...
start http://127.0.0.1:8123/

echo.
echo Backend running at http://127.0.0.1:8123
echo Close this window to stop.
pause
