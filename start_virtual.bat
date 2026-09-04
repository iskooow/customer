@echo off
rem ============================================================
rem  Customer Records - Start the server in its own window
rem  Use this if you want to keep this window free.
rem ============================================================
setlocal
cd /d "%~dp0"

rem Launch the normal start.bat in a new, separate window.
start "Customer Records - Server" cmd /k call "%~dp0start.bat"

echo.
echo   The server is starting in a separate window.
echo   Open your browser at:  http://localhost:8000
echo.
exit /b 0
