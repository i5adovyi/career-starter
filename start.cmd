@echo off
cd /d "%~dp0"
python career.py portal
if errorlevel 1 pause
