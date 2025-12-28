@echo off
chcp 65001 >nul
title Dual Camera Detection

echo ============================================================
echo        DUAL CAMERA DETECTION (Khong Calibration)
echo ============================================================
echo.

cd /d "%~dp0.."

python run_dual_cam.py

pause

