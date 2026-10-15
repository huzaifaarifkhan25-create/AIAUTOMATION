@echo off
setlocal
cd /d "%~dp0"
echo AIAUTOMATION - one-time private Gemini setup
py -3.12 -c "import sys; assert sys.version_info[:2] == (3, 12)" >nul 2>&1
if errorlevel 1 goto missing_python
if exist ".venv\Scripts\python.exe" goto install_dependency
py -3.12 -m venv .venv
if errorlevel 1 goto failed

:install_dependency
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check python-dotenv==1.2.4
if errorlevel 1 goto failed
".venv\Scripts\python.exe" backend\configure_gemini.py
if errorlevel 1 goto failed
pause
exit /b 0

:missing_python
echo Install Python 3.12 with the py launcher, then run this setup again.
pause
exit /b 1

:failed
echo Setup did not finish. No secret was added to GitHub. Read the message above.
pause
exit /b 1
