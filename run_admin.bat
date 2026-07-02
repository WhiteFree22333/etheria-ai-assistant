@echo off
cd /d "%~dp0"

:: Check admin rights
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting admin rights...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:: Run the app
echo Running as admin...
venv\Scripts\python scripts\run.py
pause
