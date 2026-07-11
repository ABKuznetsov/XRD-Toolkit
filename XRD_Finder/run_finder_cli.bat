@echo off
setlocal EnableExtensions
set "APP_ROOT=%~dp0.."
for %%I in ("%APP_ROOT%") do set "APP_ROOT=%%~fI"
set "SCI_ROOT=%LocalAppData%\Sci"
set "SCI_ENV=%SCI_ROOT%\env"
set "PYTHON_EXE=%SCI_ENV%\Scripts\python.exe"
set "SCI_APP_ROOT=%SCI_ROOT%\apps\xrd_phase_finder"

if "%~1"=="" goto usage
if "%~2"=="" goto usage

if not exist "%PYTHON_EXE%" (
    call "%APP_ROOT%\toolkit\setup_sci_env.bat"
    if errorlevel 1 exit /b 1
)

set "XRD_FINDER_DATA_DIR=%SCI_APP_ROOT%\data"
set "MPLCONFIGDIR=%SCI_APP_ROOT%\matplotlib"
set "PYTHONPATH=%APP_ROOT%\XRD_Finder;%PYTHONPATH%"
call "%PYTHON_EXE%" -m xrd_finder.apps.finder_cli "%~1" --cif "%~2"
endlocal
exit /b %ERRORLEVEL%

:usage
echo Usage:
echo   run_finder_cli.bat "pattern.txt" "phase.cif"
endlocal
exit /b 1
