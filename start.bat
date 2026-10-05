@echo off
setlocal enabledelayedexpansion
title ROOT//X Toolkit v2.4.0-PRO [Windows Launcher]
chcp 65001 >nul
color 0b

echo =============================================================
echo        ROOT//X Advanced System & Network Toolkit
echo                 Windows Quick Launcher
echo =============================================================
echo.

:: 1. Check Python installation
where python >nul 2>nul
if %errorlevel% neq 0 (
    where py >nul 2>nul
    if %errorlevel% neq 0 (
        color 0c
        echo [ERROR] Python not found in your system PATH!
        echo Please install Python 3.10+ from https://www.python.org/
        echo Make sure to check "Add Python to PATH" during installation.
        echo.
        pause
        exit /b 1
    ) else (
        set "PY_CMD=py"
    )
) else (
    set "PY_CMD=python"
)

:: 2. Check virtual environment
if not exist ".venv\Scripts\activate.bat" (
    echo [*] Setting up virtual environment (.venv)...
    %PY_CMD% -m venv .venv
    if %errorlevel% neq 0 (
        echo [!] Could not create venv, falling back to global python.
        set "RUN_PY=%PY_CMD%"
    ) else (
        call .venv\Scripts\activate.bat
        set "RUN_PY=python"
        echo [*] Installing dependencies from requirements.txt...
        pip install --upgrade pip >nul 2>nul
        pip install -r requirements.txt
    )
) else (
    call .venv\Scripts\activate.bat
    set "RUN_PY=python"
)

:: 3. Verify packages
%RUN_PY% -c "import colorama, requests, psutil, cryptography" >nul 2>nul
if %errorlevel% neq 0 (
    echo [*] Missing dependencies detected. Installing requirements...
    %RUN_PY% -m pip install -r requirements.txt
)

:: 4. Launch Toolkit
cls
%RUN_PY% main.py

if %errorlevel% neq 0 (
    echo.
    echo =============================================================
    echo [!] Toolkit process finished with code %errorlevel%.
    echo =============================================================
    pause
)
