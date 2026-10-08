@echo off
cd /d "%~dp0"
python -m http.server 8000 --directory web
if errorlevel 1 (
	echo Could not start the static dashboard. Make sure Python 3 is installed.
	pause
)
