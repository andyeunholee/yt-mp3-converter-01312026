@echo off
cd /d "%~dp0"
echo Starting YT Converter Server...
echo Please wait for the browser to open...

:: Start the Python server in the background (same window)
start /b python app.py

:: Wait 3 seconds for the server to initialize
timeout /t 3 >nul

:: Open the browser
start "" "http://127.0.0.1:5000"

:: Keep the window open so the server keeps running
echo.
echo Server is running. Close this window to stop the server.
pause
