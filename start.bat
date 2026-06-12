@echo off
setlocal
cd /d "%~dp0"

echo [start.bat] Launching AIMovie (backend first, then frontend)...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
set EXIT_CODE=%ERRORLEVEL%

if %EXIT_CODE% neq 0 (
    echo.
    echo [start.bat] Startup failed with exit code %EXIT_CODE%.
    pause
    exit /b %EXIT_CODE%
)

exit /b 0
