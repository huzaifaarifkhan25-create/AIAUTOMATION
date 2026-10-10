$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$fixtureDb = Join-Path $env:TEMP ('aia-frontend-smoke-' + [guid]::NewGuid().ToString('N') + '.sqlite3')
$apiProcess = $null
$frontendProcess = $null
try {
    $env:APP_DB_PATH = $fixtureDb
    $env:APP_API_TOKEN = 'synthetic-smoke-token-only'
    $env:BACKEND_URL = 'http://127.0.0.1:8765'
    $env:DEMO_ACCESS_CODE = 'synthetic-demo-access'
    $env:FRONTEND_SESSION_SECRET = 'synthetic-frontend-session-secret-for-smoke-only'
    $apiProcess = Start-Process -FilePath 'python' -ArgumentList @('-m', 'uvicorn', 'app.main:app', '--app-dir', 'backend', '--host', '127.0.0.1', '--port', '8765', '--workers', '1') -WorkingDirectory $repo -WindowStyle Hidden -PassThru
    $ready = $false
    for ($i = 0; $i -lt 30; $i++) {
        try { if ((Invoke-RestMethod 'http://127.0.0.1:8765/health' -TimeoutSec 2).status -eq 'ok') { $ready = $true; break } } catch { Start-Sleep -Milliseconds 500 }
    }
    if (-not $ready) { throw 'Isolated API did not start' }
    $frontendProcess = Start-Process -FilePath 'node' -ArgumentList @('node_modules/next/dist/bin/next', 'start', '-p', '3011', '-H', '127.0.0.1') -WorkingDirectory (Join-Path $repo 'frontend') -WindowStyle Hidden -PassThru
    $ready = $false
    for ($i = 0; $i -lt 30; $i++) {
        try { if ((Invoke-WebRequest 'http://127.0.0.1:3011/login' -TimeoutSec 2).StatusCode -eq 200) { $ready = $true; break } } catch { Start-Sleep -Milliseconds 500 }
    }
    if (-not $ready) { throw 'Frontend did not start' }
    & node (Join-Path $repo 'frontend\scripts\smoke-client.mjs')
    if ($LASTEXITCODE -ne 0) { throw 'Isolated HTTP smoke failed' }
}
finally {
    if ($frontendProcess -and -not $frontendProcess.HasExited) { Stop-Process -Id $frontendProcess.Id -Force }
    if ($apiProcess -and -not $apiProcess.HasExited) { Stop-Process -Id $apiProcess.Id -Force }
    foreach ($path in @($fixtureDb, "$fixtureDb-wal", "$fixtureDb-shm")) { if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Force } }
}
