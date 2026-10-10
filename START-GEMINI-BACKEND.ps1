# Starts the local FastAPI backend with a Gemini key held only in this terminal session.
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

if (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue) {
    Write-Host 'Port 8000 is already in use. Stop the current backend terminal with Ctrl+C, then run this script again.'
    exit 1
}

$privateKey = Read-Host 'Enter a Gemini API key from Google AI Studio (input is hidden)' -AsSecureString
if ($privateKey.Length -eq 0) {
    Write-Host 'No key entered. Backend was not started.'
    exit 1
}

$venvPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
$pythonPath = if (Test-Path -LiteralPath $venvPython) { $venvPython } else { 'python' }
try {
    $env:GEMINI_API_KEY = ConvertFrom-SecureString -SecureString $privateKey -AsPlainText
    Remove-Variable privateKey
    Write-Host 'Starting the local backend with Gemini enabled. Keep this terminal open; press Ctrl+C to stop.'
    & $pythonPath -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --workers 1
} finally {
    Remove-Item Env:GEMINI_API_KEY -ErrorAction SilentlyContinue
}
