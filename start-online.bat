@echo off
title Jaggery - Put website online (STABLE link)
cd /d "C:\Users\soeth.LENOVO-974\Documents\Odoo\Projects\my_project"

echo ============================================================
echo   Smart Jaggery Marketplace - going ONLINE (stable link)
echo ============================================================
echo.
echo [1/3] Starting the backend (Flask)...
start "Jaggery Backend"  cmd /k "cd /d %CD%\backend && py app.py"

echo [2/3] Starting the website (Express)...
start "Jaggery Frontend" cmd /k "cd /d %CD%\frontend && npm start"

echo      waiting a few seconds for the servers to wake up...
timeout /t 9 /nobreak >nul

echo [3/3] Opening your public link (Cloudflare Tunnel - no warning page)...
start "Jaggery PUBLIC LINK" cmd /k "cloudflared.exe tunnel --url http://localhost:3000"

echo.
echo ============================================================
echo   ALL STARTED!
echo.
echo   Your public website link appears in the "Jaggery PUBLIC LINK"
echo   window - look for a line like:
echo       https://something-random.trycloudflare.com
echo.
echo   Open THAT link on any phone/computer. No "Visit Site" page,
echo   and the styling/CSS loads correctly (unlike ngrok free).
echo.
echo   NOTE: the link is different each time you start. To get a
echo   permanent custom link, set up a named Cloudflare tunnel.
echo.
echo   Keep ALL the windows open while you use the site.
echo   To STOP the website: just close those 3 windows.
echo ============================================================
echo.
pause
