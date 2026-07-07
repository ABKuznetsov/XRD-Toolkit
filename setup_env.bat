@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if not exist "%CD%\toolkit\setup_xrd_toolkit_env.bat" (
    echo XRD_Toolkit setup script was not found:
    echo %CD%\toolkit\setup_xrd_toolkit_env.bat
    pause
    exit /b 1
)

echo Preparing shared XRD_Toolkit environment in %%LocalAppData%%\XRD_Toolkit...
echo This can take several minutes on the first run because Python packages are downloaded and configured.
call "%CD%\toolkit\setup_xrd_toolkit_env.bat"
if errorlevel 1 (
    echo.
    echo Environment setup failed. See log:
    echo %%LocalAppData%%\XRD_Toolkit\logs\setup.log
    pause
    exit /b 1
)

echo.
echo XRD_Toolkit environment is ready.
echo Launcher: XRD_Finder\launch_xrd_finder_silent.vbs
echo Diagnostic launcher: XRD_Finder\run_finder.bat
echo Logs: %%LocalAppData%%\XRD_Toolkit\logs
pause
exit /b 0