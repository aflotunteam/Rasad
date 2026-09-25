# RASAD: backend va frontendni bitta buyruq bilan ishga tushirish (Windows PowerShell).
#   .\scripts\dev.ps1            # mavjud bazadan foydalanadi
#   .\scripts\dev.ps1 -Seed      # bazani sintetik ma'lumot bilan qayta yaratadi
#   .\scripts\dev.ps1 -Install   # bog'liqliklarni o'rnatadi (birinchi marta)
param([switch]$Seed, [switch]$Install)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root 'backend'
$frontend = Join-Path $root 'frontend'
$python = Join-Path $backend '.venv\Scripts\python.exe'

$nodeDir = 'C:\Program Files\nodejs'
if (-not (Get-Command node -ErrorAction SilentlyContinue) -and (Test-Path $nodeDir)) {
    $env:PATH = "$nodeDir;$env:PATH"
}

if ($Install -or -not (Test-Path $python)) {
    Write-Host '• Python virtual muhiti va paketlar...' -ForegroundColor Cyan
    python -m venv (Join-Path $backend '.venv')
    & $python -m pip install -r (Join-Path $backend 'requirements.txt')
}
if ($Install -or -not (Test-Path (Join-Path $frontend 'node_modules'))) {
    Write-Host '• npm paketlari...' -ForegroundColor Cyan
    Push-Location $frontend; npm install; Pop-Location
}

$env:PYTHONIOENCODING = 'utf-8'
if ($Seed -or -not (Test-Path (Join-Path $backend 'rasad.db'))) {
    Write-Host '• Sintetik ma''lumot yaratilmoqda (taxminan 30 soniya)...' -ForegroundColor Cyan
    Push-Location $backend; & $python -m scripts.seed; & $python -m scripts.make_samples; Pop-Location
}

Write-Host '• API: http://127.0.0.1:8000/docs' -ForegroundColor Green
$api = Start-Process -FilePath $python -ArgumentList '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000' `
    -WorkingDirectory $backend -PassThru -NoNewWindow

Write-Host '• Veb: http://localhost:5173' -ForegroundColor Green
try {
    Push-Location $frontend
    npm run dev
}
finally {
    Pop-Location
    if ($api -and -not $api.HasExited) { Stop-Process -Id $api.Id }
}
