@echo off
setlocal
cd /d "%~dp0"

where node >nul 2>&1
if errorlevel 1 goto missing_node
where npm.cmd >nul 2>&1
if errorlevel 1 goto missing_node

set "EDGE=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
if exist "%EDGE%" goto install
set "EDGE=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
if not exist "%EDGE%" goto missing_edge

:install
echo Installing the local Edge collector library. The CRM itself does not need Node.
call npm.cmd install --prefix ".local\browser-tools" --no-save --ignore-scripts --no-audit --no-fund playwright-core@1.64.0
if errorlevel 1 goto failed
echo.
echo Local Edge collector is installed. Restart START-WINDOWS.bat, then open
echo Discover ^& import and click Check again. Review every result before importing.
pause
exit /b 0

:missing_node
echo Node.js and npm are required for the optional local Edge collector.
echo Install Node.js from https://nodejs.org/ then run this file again.
pause
exit /b 1

:missing_edge
echo Microsoft Edge was not found in its standard Windows installation folder.
echo Install or repair Edge, then run this file again.
pause
exit /b 1

:failed
echo Collector setup failed. Check the npm error above and your network connection.
pause
exit /b 1
