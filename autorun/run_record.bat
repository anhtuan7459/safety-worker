@echo off
chcp 65001 >nul
title Record Dual Camera

echo ============================================================
echo        QUAY VIDEO 2 CAMERA
echo ============================================================
echo.

cd /d "%~dp0.."

python record_dual_cam.py

pause

