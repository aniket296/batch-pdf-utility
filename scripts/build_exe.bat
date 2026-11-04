@echo off
setlocal enabledelayedexpansion

echo ============================================================================
echo  Batch PDF Studio - Windows Standalone Executable Build Pipeline
echo ============================================================================

if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
    set "PYTEST_EXE=.venv\Scripts\pytest.exe"
    set "PYINSTALLER_EXE=.venv\Scripts\pyinstaller.exe"
) else (
    set "PYTHON_EXE=python"
    set "PYTEST_EXE=pytest"
    set "PYINSTALLER_EXE=pyinstaller"
)

echo.
echo [1/3] Running automated pytest suite...
"%PYTEST_EXE%"
if errorlevel 1 (
    echo [ERROR] Unit tests failed. Aborting Windows executable build.
    exit /b 1
)

echo.
echo [2/3] Compiling standalone Windows executable via PyInstaller...
"%PYINSTALLER_EXE%" --noconfirm --clean build_windows.spec
if errorlevel 1 (
    echo [ERROR] PyInstaller compilation failed.
    exit /b 1
)

echo.
echo [3/3] Verifying generated executable artifact...
if exist "dist\BatchPDFStudio.exe" (
    echo [SUCCESS] Standalone executable built at: dist\BatchPDFStudio.exe
    exit /b 0
) else (
    echo [ERROR] Expected output dist\BatchPDFStudio.exe was not found!
    exit /b 1
)
