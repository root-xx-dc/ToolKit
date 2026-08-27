@echo off
setlocal enabledelayedexpansion
title ROOT//X TOOLKIT - Setup
chcp 65001 >nul 2>&1

echo.
echo   ============================================
echo     ROOT//X TOOLKIT -- Setup
echo   ============================================
echo.

:: -- 1. Python ---------------------------------------------------------------
echo   [*] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo   [!] Python not found.
    echo   [!] Download from: https://python.org/downloads
    echo   [!] Make sure to check "Add Python to PATH" during installation!
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo   [OK] %%v

:: -- 2. Install package ------------------------------------------------------
echo.
echo   [*] Installing package...
set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

if exist "%SCRIPT_DIR%\build_protected.py" (
    python "%SCRIPT_DIR%\build_protected.py" >nul 2>&1
)

pip install -e "%SCRIPT_DIR%" --quiet
if errorlevel 1 (
    echo   [!] pip installation failed.
    pause
    exit /b 1
)
echo   [OK] Package installed.

:: -- 3. Check PATH -----------------------------------------------------------
echo.
where rootx >nul 2>&1
if errorlevel 1 (
    echo   [!] Command 'rootx' is not yet in PATH.

    for /f "tokens=*" %%p in ('python -c "import site,os; s=site.getusersitepackages(); print(os.path.normpath(os.path.join(s,'..','..','Scripts')))" 2^>nul') do (
        setx PATH "%PATH%;%%p" >nul 2>&1
        echo   [OK] Added to PATH: %%p
        set PATH=%PATH%;%%p
    )
)

:: -- 4. Desktop shortcut -----------------------------------------------------
echo.
echo   [*] Creating desktop shortcut...

set DESKTOP=%USERPROFILE%\Desktop
set SHORTCUT_PATH=%DESKTOP%\RootX-Toolkit.lnk
set SCRIPT_PATH=%~dp0run.bat

powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell; ^
   $s = $ws.CreateShortcut('%SHORTCUT_PATH%'); ^
   $s.TargetPath = '%SCRIPT_PATH%'; ^
   $s.WorkingDirectory = '%~dp0'; ^
   $s.Description = 'ROOT//X TOOLKIT'; ^
   $s.IconLocation = '%SystemRoot%\System32\cmd.exe,0'; ^
   $s.WindowStyle = 1; ^
   $s.Save()" >nul 2>&1

if exist "%SHORTCUT_PATH%" (
    echo   [OK] Desktop shortcut: %SHORTCUT_PATH%
) else (
    echo   [!] Could not create shortcut. Use run.bat instead.
)

:: -- 5. Clear license cache --------------------------------------------------
echo.
echo   [*] Clearing license cache...
if exist "%APPDATA%\rootx-toolkit\license_cache.bin" (
    del /f /q "%APPDATA%\rootx-toolkit\license_cache.bin"
    echo   [OK] License cache cleared.
) else if exist "%APPDATA%\rootx-toolkit\license_cache.json" (
    del /f /q "%APPDATA%\rootx-toolkit\license_cache.json"
    echo   [OK] License cache cleared.
) else (
    echo   [OK] No cache found, skipping.
)

:: -- 6. Done -----------------------------------------------------------------
echo.
echo   ============================================
echo     Setup complete!
echo.
echo     Click the desktop shortcut
echo     or run:  rootx
echo   ============================================
echo.
pause
