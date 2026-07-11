@echo off
setlocal EnableExtensions
set "APP_ROOT=%~dp0.."
for %%I in ("%APP_ROOT%") do set "APP_ROOT=%%~fI"
set "SCI_ROOT=%LocalAppData%\Sci"
set "SCI_ENV=%SCI_ROOT%\env"
set "SCI_APP_ROOT=%SCI_ROOT%\apps\xrd_phase_finder"
set "PYTHON_EXE=%SCI_ENV%\Scripts\python.exe"
set "LOG_FILE=%SCI_ROOT%\logs\xrd_finder_console.log"

if not exist "%PYTHON_EXE%" (
    call "%APP_ROOT%\toolkit\setup_sci_env.bat"
    if errorlevel 1 (
        echo Sci environment setup failed.
        echo See log: %SCI_ROOT%\logs\setup.log
        pause
        exit /b 1
    )
)

if not exist "%PYTHON_EXE%" (
    echo Sci Python executable was not found:
    echo %PYTHON_EXE%
    pause
    exit /b 1
)

if not exist "%SCI_ROOT%\logs" mkdir "%SCI_ROOT%\logs"
if not exist "%SCI_APP_ROOT%" mkdir "%SCI_APP_ROOT%"
set "PYTHONDONTWRITEBYTECODE=1"
set "XRD_FINDER_DATA_DIR=%SCI_APP_ROOT%\data"
set "MPLCONFIGDIR=%SCI_APP_ROOT%\matplotlib"
set "QT_OPENGL=software"
set "QT_QUICK_BACKEND=software"
set "QT_ANGLE_PLATFORM=warp"
set "PYTHONPATH=%APP_ROOT%\XRD_Finder;%PYTHONPATH%"

echo Starting XRD Phase Finder with console diagnostics...
echo Log file: %LOG_FILE%
echo [%date% %time%] Starting XRD Phase Finder > "%LOG_FILE%"
call "%PYTHON_EXE%" -m xrd_finder.apps.finder_gui %* 1>> "%LOG_FILE%" 2>&1
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" (
    echo.
    echo XRD Phase Finder exited with code %EXIT_CODE%.
    echo Last log lines:
    powershell -NoProfile -ExecutionPolicy Bypass -Command "if (Test-Path '%LOG_FILE%') { Get-Content -LiteralPath '%LOG_FILE%' -Tail 30 }"
    pause
)
endlocal & exit /b %EXIT_CODE%
