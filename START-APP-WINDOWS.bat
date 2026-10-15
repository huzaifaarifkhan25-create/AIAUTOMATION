@echo off
setlocal
cd /d "%~dp0"
echo Starting the API and current purple workspace in separate windows.
echo Stop both windows with Ctrl+C when you finish using the app.
start "AIAUTOMATION backend" cmd /k call "%~dp0START-WINDOWS.bat"
start "AIAUTOMATION workspace" cmd /k call "%~dp0START-FRONTEND-WINDOWS.bat"
echo.
echo Once both servers are ready, open http://127.0.0.1:3000
echo The older CRM remains at http://127.0.0.1:8000/app/
pause
