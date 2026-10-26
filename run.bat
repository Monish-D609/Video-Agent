@echo off
title Video Agent - Starting Cloud Backend
color 0b
echo ============================================================
echo   Video Agent - Starting AWS Cloud Backend Infrastructure
echo ============================================================
echo.
echo [1/3] Contacting AWS in region ap-south-1...
echo [2/3] Powering on EC2 instance and Docker containers...
echo [3/3] Restoring persistent state from Amazon S3...
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start.ps1"

echo.
echo ============================================================
echo   Cloud backend is READY for demonstration!
echo   (Press any key to close this launcher. The server stays on in AWS.)
echo ============================================================
pause >nul
