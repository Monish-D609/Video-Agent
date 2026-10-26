@echo off
title Video Agent - Stopping Cloud Backend
color 0e
echo ============================================================
echo   Video Agent - Stopping AWS Cloud Backend (Zero-Cost Mode)
echo ============================================================
echo.
echo [1/3] Syncing latest transcripts and session state to S3...
echo [2/3] Halting EC2 instance to pause compute billing...
echo [3/3] Releasing public IPv4 address...
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\stop.ps1"

echo.
echo ============================================================
echo   All credit-consuming AWS resources have been STOPPED!
echo   Ongoing compute and IPv4 charges: $0.00 / hour.
echo   (Press any key to close this window.)
echo ============================================================
pause >nul