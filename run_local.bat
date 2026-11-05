@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment in .venv ...
    python -m venv .venv
    if errorlevel 1 goto :error
)

echo Installing / updating dependencies ...
".venv\Scripts\pip" install -r requirements.txt
if errorlevel 1 goto :error

echo Launching Batch PDF Studio from source ...
".venv\Scripts\python" -m src.main
if errorlevel 1 goto :error

endlocal
exit /b 0

:error
echo.
echo [ERROR] Execution failed. See the messages above for details.
pause
endlocal
exit /b 1

