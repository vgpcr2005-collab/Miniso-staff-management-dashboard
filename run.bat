@echo off
cd /d "%~dp0"
python app_server.py
if errorlevel 1 (
	echo Could not start the MINISO server. Make sure Python 3 is installed.
	pause
)
