@echo off
setlocal
cd /d "%~dp0"

if "%~1"=="" goto usage
if "%~2"=="" goto usage

if not exist ".venv\Scripts\python.exe" (
    echo Shared Toolkit environment was not found.
    echo Run setup_env.bat first.
    pause
    exit /b 1
)

call ".venv\Scripts\python.exe" -m xrd_manager.apps.finder_cli "%~1" --cif "%~2"
endlocal
exit /b 0

:usage
echo Usage:
echo   run_finder_cli.bat "pattern.txt" "phase.cif"
endlocal
exit /b 1
