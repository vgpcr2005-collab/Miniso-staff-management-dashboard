@echo off
cd /d "%~dp0"
python server.py
if errorlevel 1 (
	echo Could not start the dashboard backend. Make sure Python 3.10 or newer is installed.
	pause
)
