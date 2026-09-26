# RASAD: backend va frontendni doimiy ishlatib turuvchi nazoratchi (watchdog).
# Jarayon to'xtasa yoki /health javob bermay qolsa, avtomatik qayta ishga tushiriladi.
#   .\scripts\serve.ps1                 # joriy oynada
#   .\scripts\install-autostart.ps1     # Windows'ga kirganda avtomatik ishga tushirish
# Loglar: logs\api.log, logs\web.log, logs\watchdog.log

$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root 'backend'
$frontend = Join-Path $root 'frontend'
$python = Join-Path $backend '.venv\Scripts\python.exe'
$node = 'C:\Program Files\nodejs\node.exe'
$vite = Join-Path $frontend 'node_modules\vite\bin\vite.js'
$logs = Join-Path $root 'logs'
New-Item -ItemType Directory -Force $logs | Out-Null
$env:PYTHONIOENCODING = 'utf-8'

function Log($msg) {
    $line = "{0:yyyy-MM-dd HH:mm:ss}  {1}" -f (Get-Date), $msg
    Add-Content -Path (Join-Path $logs 'watchdog.log') -Value $line -Encoding utf8
    Write-Host $line
}

# Bir vaqtda faqat bitta nazoratchi ishlashi uchun
$mutex = New-Object System.Threading.Mutex($false, 'Global\RasadWatchdog')
if (-not $mutex.WaitOne(0)) { Write-Host 'RASAD nazoratchisi allaqachon ishlayapti.'; exit 0 }

function Stop-Port($port) {
    Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue |
        ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
}

function Start-Api {
    Stop-Port 8000
    Log 'API ishga tushirilmoqda (http://127.0.0.1:8000)'
    Start-Process -FilePath $python -WorkingDirectory $backend -WindowStyle Hidden -PassThru `
        -ArgumentList '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000' `
        -RedirectStandardOutput (Join-Path $logs 'api.log') -RedirectStandardError (Join-Path $logs 'api.err.log')
}

function Start-Web {
    Stop-Port 5173
    Log 'Veb ishga tushirilmoqda (http://localhost:5173)'
    Start-Process -FilePath $node -WorkingDirectory $frontend -WindowStyle Hidden -PassThru `
        -ArgumentList "`"$vite`"", '--host', '127.0.0.1' `
        -RedirectStandardOutput (Join-Path $logs 'web.log') -RedirectStandardError (Join-Path $logs 'web.err.log')
}

function Test-Url($url) {
    try { (Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 10).StatusCode -eq 200 } catch { $false }
}

if (-not (Test-Path (Join-Path $backend 'rasad.db'))) {
    Log 'Baza topilmadi, sintetik ma''lumot yaratilmoqda'
    Push-Location $backend; & $python -m scripts.seed; Pop-Location
}

$api = Start-Api
$web = Start-Web
$apiFails = 0; $webFails = 0
Start-Sleep -Seconds 20

try {
    while ($true) {
        if ($api.HasExited) { Log "API to'xtadi (kod $($api.ExitCode)), qayta ishga tushirilmoqda"; $api = Start-Api; $apiFails = 0; Start-Sleep 15 }
        elseif (-not (Test-Url 'http://127.0.0.1:8000/api/v1/health')) {
            $apiFails++
            if ($apiFails -ge 3) { Log 'API javob bermayapti, qayta ishga tushirilmoqda'; Stop-Process -Id $api.Id -Force -ErrorAction SilentlyContinue; $api = Start-Api; $apiFails = 0; Start-Sleep 15 }
        } else { $apiFails = 0 }

        if ($web.HasExited) { Log "Veb to'xtadi (kod $($web.ExitCode)), qayta ishga tushirilmoqda"; $web = Start-Web; $webFails = 0; Start-Sleep 15 }
        elseif (-not (Test-Url 'http://127.0.0.1:5173/')) {
            $webFails++
            if ($webFails -ge 3) { Log 'Veb javob bermayapti, qayta ishga tushirilmoqda'; Stop-Process -Id $web.Id -Force -ErrorAction SilentlyContinue; $web = Start-Web; $webFails = 0; Start-Sleep 15 }
        } else { $webFails = 0 }

        Start-Sleep -Seconds 20
    }
}
finally {
    Log 'Nazoratchi to''xtatildi'
    foreach ($p in @($api, $web)) { if ($p -and -not $p.HasExited) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue } }
    $mutex.ReleaseMutex()
}
