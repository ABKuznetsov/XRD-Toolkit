@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Shared Toolkit environment was not found.
    echo Run setup_env.bat first.
    pause
    exit /b 1
)

call ".venv\Scripts\python.exe" -m xrd_manager.apps.finder_gui %*
endlocal
