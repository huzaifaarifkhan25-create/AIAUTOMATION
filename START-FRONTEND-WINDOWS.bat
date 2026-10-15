@echo off
setlocal
cd /d "%~dp0frontend"
echo AIAUTOMATION - current purple workspace
node --version >nul 2>&1
if errorlevel 1 goto missing_node
call npm.cmd --version >nul 2>&1
if errorlevel 1 goto missing_node
echo Installing the locked frontend dependencies. Internet is needed initially.
call npm.cmd ci --no-audit --no-fund
if errorlevel 1 goto failed
if not defined BACKEND_URL set "BACKEND_URL=http://127.0.0.1:8000"
echo.
echo Open http://127.0.0.1:3000 after the server starts.
echo Keep the backend window open too. Use Register to create your first account.
echo Your records stay in the backend .local folder.
call npm.cmd run dev -- --hostname 127.0.0.1 --port 3000
if errorlevel 1 goto failed
exit /b 0

:missing_node
echo Install Node.js 24 LTS from https://nodejs.org and reopen this file.
pause
exit /b 1

:failed
echo Read the error above. If port 3000 is occupied, stop the other frontend first.
echo Do not share API keys when reporting an error.
pause
exit /b 1
