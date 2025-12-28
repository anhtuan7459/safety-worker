@echo off
chcp 65001 >nul
title Dual Camera Detection System - GUI

cd /d "%~dp0.."

python gui\main_app.py

pause



