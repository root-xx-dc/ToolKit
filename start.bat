@echo off
title ROOT//X Toolkit v2.4.0-PRO [Launcher]
cd /d "%~dp0"
color 0b

echo =============================================================
echo        ROOT//X Advanced System & Network Toolkit
echo                 Windows Quick Launcher
echo =============================================================
echo.

:: 1. Detect Python
set "PYTHON_EXE="

python --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_EXE=python"
    goto :PYTHON_FOUND
)

py -3 --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_EXE=py -3"
    goto :PYTHON_FOUND
)

py --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_EXE=py"
    goto :PYTHON_FOUND
)

python3 --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_EXE=python3"
    goto :PYTHON_FOUND
)

:: If Python is not found
color 0c
echo [BLAD / ERROR] Nie znaleziono Pythona w systemie Windows!
echo [!] Python 3.10+ nie jest zainstalowany lub nie dodano go do zmiennej PATH.
echo.
echo KROKI NAPRAWY:
echo 1. Pobierz Pythona z: https://www.python.org/downloads/
echo 2. Podczas instalacji ZAZNACZ pole: "Add Python to PATH" / "Add python.exe to PATH"
echo 3. Po instalacji uruchom ponownie start.bat.
echo.
pause
exit /b 1

:PYTHON_FOUND
echo [*] Wykryto interpreter: %PYTHON_EXE%
%PYTHON_EXE% --version
echo.

:: 2. Check and install dependencies
echo [*] Sprawdzanie wymaganych bibliotek...
%PYTHON_EXE% -m pip install --quiet --upgrade pip >nul 2>&1

%PYTHON_EXE% -c "import colorama, requests, psutil, cryptography, pypresence" >nul 2>&1
if %errorlevel% neq 0 (
    echo [*] Instalowanie brakujacych bibliotek z requirements.txt...
    %PYTHON_EXE% -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [!] Blad podczas instalacji bibliotek pip. Proba kontynuacji...
    )
) else (
    echo [*] Wszystkie wymagane biblioteki sa zainstalowane.
)

echo.
echo [*] Uruchamianie ROOT//X Toolkit...
echo.

:: 3. Run main.py
%PYTHON_EXE% main.py

echo.
echo =============================================================
echo [*] Program zostal zakonczony.
echo =============================================================
pause
