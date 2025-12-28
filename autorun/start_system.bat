@echo off
chcp 65001 >nul
title Dual Camera Detection System

echo ============================================================
echo        DUAL CAMERA DETECTION SYSTEM
echo ============================================================
echo.

cd /d "%~dp0.."

echo [1/2] Dang chay Calibration...
echo.
python setup_calibration.py

echo.
echo [2/2] Dang chay Dual Camera Detection...
echo.
python run_dual_cam.py

echo.
echo ============================================================
echo        DA HOAN TAT
echo ============================================================
pause
