@echo off
rem ============================================================
rem  Customer Records - One-time setup
rem  Run this ONCE on a new computer before using start.bat
rem ============================================================
setlocal
title Customer Records - Setup

cd /d "%~dp0"

echo.
echo ============================================================
echo   Customer Records - Setup
echo ============================================================
echo.

rem --- Locate Python -------------------------------------------------
where python >nul 2>nul
if errorlevel 1 (
    where py >nul 2>nul
    if errorlevel 1 (
        echo [ERROR] Python was not found.
        echo.
        echo Please install Python first from https://www.python.org/downloads/
        echo and make sure you tick "Add Python to PATH" during installation.
        echo.
        pause
        exit /b 1
    )
)

rem --- Create virtual environment -------------------------------------
if not exist "venv\Scripts\activate.bat" (
    echo [1/3] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Could not create the virtual environment.
        pause
        exit /b 1
    )
) else (
    echo [1/3] Virtual environment already exists, skipping.
)

rem --- Activate and install dependencies ------------------------------
call "venv\Scripts\activate.bat"
echo [2/3] Installing dependencies from requirements.txt...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies. Check your internet connection.
    pause
    exit /b 1
)

rem --- Run database migrations ----------------------------------------
echo [3/3] Applying database migrations...
python manage.py migrate
if errorlevel 1 (
    echo [ERROR] Database migration failed.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Setup complete!
echo   Now run start.bat to launch the server.
echo ============================================================
echo.
pause
exit /b 0
