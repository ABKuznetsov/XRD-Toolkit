@echo off
setlocal EnableExtensions
set "APP_ROOT=%~dp0.."
for %%I in ("%APP_ROOT%") do set "APP_ROOT=%%~fI"
set "XRD_TOOLKIT_ROOT=%LocalAppData%\XRD_Toolkit"
set "XRD_TOOLKIT_ENV=%XRD_TOOLKIT_ROOT%\env"
set "PYTHON_EXE=%XRD_TOOLKIT_ENV%\Scripts\python.exe"

if "%~1"=="" goto usage
if "%~2"=="" goto usage

if not exist "%PYTHON_EXE%" (
    call "%APP_ROOT%\toolkit\setup_xrd_toolkit_env.bat"
    if errorlevel 1 exit /b 1
)

set "PYTHONPATH=%APP_ROOT%\XRD_Finder;%PYTHONPATH%"
call "%PYTHON_EXE%" -m xrd_finder.apps.finder_cli "%~1" --cif "%~2"
endlocal
exit /b %ERRORLEVEL%

:usage
echo Usage:
echo   run_finder_cli.bat "pattern.txt" "phase.cif"
endlocal
exit /b 1