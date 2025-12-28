@echo off
chcp 65001 >nul
title Camera Calibration

echo ============================================================
echo        CAMERA CALIBRATION
echo ============================================================
echo.

cd /d "%~dp0.."

python setup_calibration.py

pause

