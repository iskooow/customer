@echo off
rem ============================================================
rem  Customer Records - Start the server
rem  Double-click this every time you want to run the app.
rem ============================================================
setlocal
title Customer Records - Server
cd /d "%~dp0"

echo.
echo ============================================================
echo   Customer Records - Starting server
echo ============================================================
echo.

rem --- Check the virtual environment exists ---------------------------
if not exist "venv\Scripts\activate.bat" (
    echo [INFO] Virtual environment not found - running setup first.
    call "%~dp0setup.bat"
    if errorlevel 1 exit /b 1
)

call "venv\Scripts\activate.bat"

rem --- Apply any pending migrations -----------------------------------
echo [1/3] Checking database migrations...
python manage.py migrate >nul
if errorlevel 1 (
    echo [ERROR] Migration failed. Run setup.bat again.
    pause
    exit /b 1
)

rem --- Refresh expiry alerts ------------------------------------------
echo [2/3] Refreshing expiry alerts...
python manage.py check_expiries >nul 2>nul

rem --- Start the server -----------------------------------------------
echo [3/3] Server starting...
echo.
echo   Open your browser at:  http://localhost:8000
echo   Press Ctrl+C in this window to stop the server.
echo.

python manage.py runserver 0.0.0.0:8000

echo.
echo Server stopped.
pause
exit /b 0
