@echo off
chcp 65001 >nul
title Dual Camera Detection System - C# GUI

cd /d "%~dp0..\gui_csharp"

echo ============================================================
echo   Building C# Application...
echo ============================================================

dotnet run

pause



