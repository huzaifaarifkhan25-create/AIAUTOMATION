@echo off
setlocal
cd /d "%~dp0"

echo AIAUTOMATION - Windows laptop setup
echo.
py -3.12 -c "import sys; assert sys.version_info[:2] == (3, 12)" >nul 2>&1
if errorlevel 1 goto missing_python

if exist ".venv\Scripts\python.exe" goto install_dependencies
py -3.12 -m venv .venv
if errorlevel 1 goto setup_failed

:install_dependencies
echo Installing or checking dependencies. Internet is needed on the first launch.
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r backend\requirements.txt
if errorlevel 1 goto setup_failed
".venv\Scripts\python.exe" -m pip check
if errorlevel 1 goto setup_failed

echo.
echo After "Application startup complete" appears, open your browser and type:
echo http://127.0.0.1:8000/app/
echo.
echo Keep this window open while using the app. Press Ctrl+C to stop it.
echo Your local records will be saved in .local\backend.sqlite3.
echo.
".venv\Scripts\python.exe" -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --workers 1
if errorlevel 1 goto startup_failed
exit /b 0

:missing_python
echo Python 3.12 and the Windows Python launcher are required.
echo Install Python 3.12 from the official Python website, including the launcher.
echo See WINDOWS-START-HERE.md, then run this file again.
pause
exit /b 1

:setup_failed
echo.
echo Setup failed. Read the error above; check your internet connection and Python installation.
echo Share the error message if you need help. Do not share credentials.
pause
exit /b 1

:startup_failed
echo.
echo Startup failed. If port 8000 is already in use, close the other app window first.
echo Read the error above and share it if you need help. Do not share credentials.
pause
exit /b 1
