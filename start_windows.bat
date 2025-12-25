@echo off
cd /d "%~dp0"
echo Starting ResearchMind on Windows...
powershell -NoProfile -ExecutionPolicy Bypass -File "start_windows.ps1"
pause
