@echo off
title Smart Jaggery Mart - START
cd /d "%~dp0"

if not exist "backend\.env" (
    echo.
    echo   backend\.env not found - please run SETUP.bat first.
    echo.
    pause
    exit /b 1
)
if not exist "frontend\node_modules" (
    echo.
    echo   frontend\node_modules not found - please run SETUP.bat first.
    echo.
    pause
    exit /b 1
)

echo ============================================================
echo   Smart Jaggery Mart - starting...
echo ============================================================
echo.
echo [1/2] Starting the backend (Flask)...
where py >nul 2>nul
if errorlevel 1 (
    start "Jaggery Backend"  cmd /k "cd /d %~dp0backend && python app.py"
) else (
    start "Jaggery Backend"  cmd /k "cd /d %~dp0backend && py app.py"
)

echo [2/2] Starting the website (Express)...
start "Jaggery Frontend" cmd /k "cd /d %~dp0frontend && npm start"

echo      waiting a few seconds for the servers to wake up...
timeout /t 9 /nobreak >nul

echo      opening the website...
start "" http://localhost:3000

echo.
echo ============================================================
echo   ALL STARTED!
echo.
echo   Website:  http://localhost:3000
echo.
echo   Keep BOTH the "Backend" and "Frontend" windows open while
echo   you use the site.
echo   To STOP the website: just close those 2 windows.
echo ============================================================
echo.
pause
