@echo off
setlocal
title ROOT//X TOOLKIT

where rootx >nul 2>&1
if %errorlevel% equ 0 (
    rootx %*
) else (
    python -m rootx %*
)

if %errorlevel% neq 0 (
    echo.
    echo [!] Program exited with code %errorlevel%.
    pause
)
