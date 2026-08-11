@echo off
title Stopping DBPlane Server
echo Stopping DBPlane Server...

:: Find and kill the process running on port 8000
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo Killing process PID: %%a
    taskkill /PID %%a /F >nul 2>&1
)

echo DBPlane Server stopped.
timeout /t 2 >nul
