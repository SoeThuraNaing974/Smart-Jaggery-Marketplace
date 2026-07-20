@echo off
title Jaggery - Run website LOCALLY
cd /d "%~dp0"

echo ============================================================
echo   Smart Jaggery Marketplace - running LOCALLY (this PC only)
echo ============================================================
echo.
echo [1/2] Starting the backend (Flask)...
start "Jaggery Backend"  cmd /k "cd /d %~dp0backend && py app.py"

echo [2/2] Starting the website (Express)...
start "Jaggery Frontend" cmd /k "cd /d %~dp0frontend && npm start"

echo      waiting a few seconds for the servers to wake up...
timeout /t 9 /nobreak >nul

echo      opening your local website...
start "" http://localhost:3000

echo.
echo ============================================================
echo   ALL STARTED!
echo.
echo   Your website is now running on THIS computer only:
echo       http://localhost:3000
echo.
echo   It is NOT shared online - no public link is created.
echo.
echo   Keep BOTH the "Backend" and "Frontend" windows open while
echo   you use the site.
echo   To STOP the website: just close those 2 windows.
echo ============================================================
echo.
pause
