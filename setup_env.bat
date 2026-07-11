@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if not exist "%CD%\toolkit\setup_sci_env.bat" (
    echo Sci environment setup script was not found:
    echo %CD%\toolkit\setup_sci_env.bat
    pause
    exit /b 1
)

echo Preparing shared Sci environment in %%LocalAppData%%\Sci...
echo If you used an older test build, close the app and delete %%LocalAppData%%\XRD_Toolkit manually before setup.
call "%CD%\toolkit\setup_sci_env.bat"
if errorlevel 1 (
    echo.
    echo Environment setup failed. See log:
    echo %%LocalAppData%%\Sci\logs\setup.log
    pause
    exit /b 1
)

echo.
echo Sci environment is ready.
echo Launcher: XRD_Finder\launch_xrd_finder_silent.vbs
echo Diagnostic launcher: XRD_Finder\run_finder.bat
echo Logs: %%LocalAppData%%\Sci\logs
pause
exit /b 0
