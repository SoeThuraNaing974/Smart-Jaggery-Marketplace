@echo off
setlocal enabledelayedexpansion
title Smart Jaggery Mart - SETUP
cd /d "%~dp0"

echo ============================================================
echo   Smart Jaggery Mart - ONE-TIME SETUP
echo ============================================================
echo.
echo   This will:
echo     1. Check that Python, Node.js and PostgreSQL are installed
echo     2. Install the backend (Flask) Python packages
echo     3. Install the frontend (Express) Node packages
echo     4. Create the "jaggery_db" database
echo     5. Create the .env configuration files
echo     6. Load demo data (or restore the full backup)
echo.
pause
echo.

REM ---------- 1. Check prerequisites ----------
echo [1/6] Checking prerequisites...

set "PY_CMD=py"
where py >nul 2>nul
if errorlevel 1 (
    set "PY_CMD=python"
    where python >nul 2>nul
    if errorlevel 1 (
        echo   [X] Python was NOT found.
        echo       Install it from https://www.python.org/downloads/
        echo       IMPORTANT: tick "Add python.exe to PATH" during install.
        goto :fail
    )
)
echo   [OK] Python found

where node >nul 2>nul
if errorlevel 1 (
    echo   [X] Node.js was NOT found.
    echo       Install it from https://nodejs.org/  ^(LTS version^)
    goto :fail
)
echo   [OK] Node.js found

REM Find psql - on PATH first, then in the usual install folders
set "PSQL="
where psql >nul 2>nul
if not errorlevel 1 set "PSQL=psql"
if not defined PSQL (
    for /d %%D in ("C:\Program Files\PostgreSQL\*") do (
        if exist "%%D\bin\psql.exe" set "PSQL=%%D\bin\psql.exe"
    )
)
if not defined PSQL (
    echo   [X] PostgreSQL was NOT found.
    echo       Install it from https://www.postgresql.org/download/windows/
    echo       Remember the password you choose for the "postgres" user.
    goto :fail
)
echo   [OK] PostgreSQL found: !PSQL!
echo.

REM ---------- 2. Database connection details ----------
echo [2/6] Database connection
echo   Press ENTER to accept the value shown in [brackets].
echo.
set "PGPORT=5432"
set /p PGPORT="  PostgreSQL port [5432]: "
set "PGPASS=postgres"
set /p PGPASS="  Password of the 'postgres' user [postgres]: "
set "PGPASSWORD=%PGPASS%"

"!PSQL!" -U postgres -h localhost -p %PGPORT% -c "SELECT 1;" >nul 2>nul
if errorlevel 1 (
    echo.
    echo   [X] Could not connect to PostgreSQL on port %PGPORT%.
    echo       Check that the PostgreSQL service is running and the
    echo       port/password are correct, then run SETUP.bat again.
    goto :fail
)
echo   [OK] Connected to PostgreSQL
echo.

REM ---------- 3. Create the database ----------
echo [3/6] Creating database "jaggery_db" (skipped if it already exists)...
"!PSQL!" -U postgres -h localhost -p %PGPORT% -tc "SELECT 1 FROM pg_database WHERE datname='jaggery_db'" | findstr "1" >nul
if errorlevel 1 (
    "!PSQL!" -U postgres -h localhost -p %PGPORT% -c "CREATE DATABASE jaggery_db;" >nul
    if errorlevel 1 (
        echo   [X] Could not create the database.
        goto :fail
    )
    echo   [OK] Database created
    set "DB_IS_NEW=1"
) else (
    echo   [OK] Database already exists - keeping it
    set "DB_IS_NEW="
)
echo.

REM ---------- 4. Write the .env files ----------
echo [4/6] Writing configuration (.env files)...
set "JWT_SECRET="
for /f %%S in ('powershell -NoProfile -Command "$b=New-Object byte[] 32; [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b); -join ($b | ForEach-Object { $_.ToString('x2') })"') do set "JWT_SECRET=%%S"
if not defined JWT_SECRET set "JWT_SECRET=change-me-%RANDOM%%RANDOM%%RANDOM%"

> "backend\.env" (
    echo DATABASE_URL=postgresql://postgres:%PGPASS%@localhost:%PGPORT%/jaggery_db
    echo JWT_SECRET=%JWT_SECRET%
    echo JWT_EXP_HOURS=12
    echo UPLOAD_FOLDER=uploads
)
> "frontend\.env" (
    echo PORT=3000
    echo API_BASE=http://127.0.0.1:5000
    echo JWT_SECRET=%JWT_SECRET%
)
echo   [OK] backend\.env and frontend\.env created
echo.

REM ---------- 5. Install packages ----------
echo [5/6] Installing packages (this can take a few minutes)...
echo.
echo   --- Backend: Python packages ---
%PY_CMD% -m pip install -r "backend\requirements.txt"
if errorlevel 1 (
    echo   [X] pip install failed. Check your internet connection.
    goto :fail
)
echo.
echo   --- Frontend: Node packages ---
pushd frontend
call npm install
if errorlevel 1 (
    popd
    echo   [X] npm install failed. Check your internet connection.
    goto :fail
)
popd
echo.

REM ---------- 6. Load data ----------
echo [6/6] Loading data...
set "LOADMODE=1"
if defined DB_IS_NEW (
    echo.
    echo   How do you want to start?
    echo     1 = Fresh demo data  ^(recommended^)
    echo     2 = Restore the full backup ^(jaggery_db_backup.sql^)
    set /p LOADMODE="  Choose 1 or 2 [1]: "
)
if "!LOADMODE!"=="2" (
    "!PSQL!" -U postgres -h localhost -p %PGPORT% -d jaggery_db -f "jaggery_db_backup.sql" >nul
    echo   [OK] Backup restored
) else (
    if defined DB_IS_NEW (
        pushd backend
        %PY_CMD% seed.py
        popd
    ) else (
        echo   [OK] Existing database kept - nothing loaded
    )
)

echo.
echo ============================================================
echo   SETUP COMPLETE!
echo.
echo   To run the website: double-click  START.bat
echo.
echo   Demo logins (if you chose fresh demo data):
echo     admin@jaggery.local    /  admin123
echo     staff@jaggery.local    /  staff123
echo     customer@jaggery.local /  cust123
echo ============================================================
echo.
pause
exit /b 0

:fail
echo.
echo   Setup did not finish. Fix the problem above and run
echo   SETUP.bat again - it is safe to re-run.
echo.
pause
exit /b 1
