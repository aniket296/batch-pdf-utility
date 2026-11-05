@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0\.."

echo ============================================================================
echo  Batch PDF Studio - Windows Inno Setup Installer Build Pipeline
echo ============================================================================

echo.
echo [1/3] Building and verifying standalone PyInstaller executable...
call "scripts\build_exe.bat"
if errorlevel 1 (
    echo [ERROR] Standalone executable build failed. Aborting installer creation.
    exit /b 1
)

echo.
echo [2/3] Locating Inno Setup Compiler (ISCC.exe)...
set "ISCC_EXE="

where iscc >nul 2>nul
if not errorlevel 1 (
    for /f "delims=" %%I in ('where iscc') do (
        set "ISCC_EXE=%%I"
        goto :found_iscc
    )
)

if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set "ISCC_EXE=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    goto :found_iscc
)

if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set "ISCC_EXE=C:\Program Files\Inno Setup 6\ISCC.exe"
    goto :found_iscc
)

if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" (
    set "ISCC_EXE=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
    goto :found_iscc
)

echo [ERROR] Inno Setup 6 Compiler (ISCC.exe) was not found on this machine.
echo         Install Inno Setup 6 from https://jrsoftware.org/isdl.php or add ISCC.exe to PATH.
exit /b 1

:found_iscc
echo Found Inno Setup Compiler: "%ISCC_EXE%"

echo.
echo [3/3] Compiling installer\setup.iss...
"%ISCC_EXE%" "installer\setup.iss"
if errorlevel 1 (
    echo [ERROR] Inno Setup compilation failed.
    exit /b 1
)

if exist "dist_installer\BatchPDFStudio_Setup.exe" (
    echo.
    echo ============================================================================
    echo [SUCCESS] Windows Installer is ready at:
    echo           dist_installer\BatchPDFStudio_Setup.exe
    echo           Ready for local testing or uploading to GitHub Releases!
    echo ============================================================================
    exit /b 0
) else (
    echo [ERROR] Expected installer dist_installer\BatchPDFStudio_Setup.exe was not found!
    exit /b 1
)

