@echo off
setlocal
cd /d "%~dp0"
echo AIAutomation - local n8n inquiry automation
docker info >nul 2>&1
if errorlevel 1 goto missing_docker
docker container inspect aiautomation-n8n >nul 2>&1
if not errorlevel 1 goto existing
docker run -d --name aiautomation-n8n --restart unless-stopped -p 127.0.0.1:5678:5678 -v aiautomation-n8n-data:/home/node/.n8n -e N8N_HOST=127.0.0.1 -e N8N_PROTOCOL=http -e N8N_SECURE_COOKIE=false -e N8N_DIAGNOSTICS_ENABLED=false -e N8N_PERSONALIZATION_ENABLED=false -e N8N_VERSION_NOTIFICATIONS_ENABLED=false -e N8N_TEMPLATES_ENABLED=false -e N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS=true n8nio/n8n@sha256:526daa38b68e923cc00c5280d18b4da5d489f115a73bdbf3b8e452b184197a9a
if errorlevel 1 goto failed
goto ready
:existing
docker start aiautomation-n8n
if errorlevel 1 goto failed
:ready
echo.
echo Wait a few seconds, then open http://127.0.0.1:5678
echo Create your local n8n owner account. No paid n8n account is required.
echo In n8n: Settings - n8n API - Create an API key.
echo In AIAutomation: Automations - Connect n8n. Paste that key there.
echo Your n8n workflows are saved in the Docker volume aiautomation-n8n-data.
pause
exit /b 0
:missing_docker
echo Install and start Docker Desktop, using Linux containers, then run this file again.
echo Download: https://www.docker.com/products/docker-desktop/
pause
exit /b 1
:failed
echo n8n did not start. Read the error above. Existing local data was not deleted.
pause
exit /b 1
