@echo off
title DBPlane Server
cd /d "d:\Siva Sai\MyProjects\dbplane\dbplane"

:: Check if already running
netstat -ano | findstr ":8000" >nul 2>&1
if %errorlevel%==0 (
    echo DBPlane is already running on port 8000.
    echo Opening browser...
    start http://127.0.0.1:8000/
    timeout /t 3 >nul
    exit /b 0
)

echo ============================================
echo   Starting DBPlane Server...
echo   URL: http://127.0.0.1:8000/
echo   Press Ctrl+C to stop
echo ============================================
echo.

:: Start the Django development server
python manage.py runserver 0.0.0.0:8000
