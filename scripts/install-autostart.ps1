# RASAD nazoratchisini Windows'ga kirganda avtomatik ishga tushadigan qilib ro'yxatdan o'tkazadi.
#   .\scripts\install-autostart.ps1            # o'rnatish va darhol ishga tushirish
#   .\scripts\install-autostart.ps1 -Remove    # o'chirish
param([switch]$Remove)

$name = 'RASAD Server'
$serve = Join-Path $PSScriptRoot 'serve.ps1'

if ($Remove) {
    Stop-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $name -Confirm:$false -ErrorAction SilentlyContinue
    foreach ($port in 8000, 5173) {
        Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue |
            ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
    }
    Write-Host "'$name' o'chirildi."
    exit 0
}

$action = New-ScheduledTaskAction -Execute 'powershell.exe' `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$serve`""
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
# Nazoratchining o'zi to'xtasa ham, Windows uni har daqiqada qayta ishga tushiradi
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Settings $settings `
    -Description 'RASAD backend (8000) va frontend (5173) nazoratchisi' -Force | Out-Null
Start-ScheduledTask -TaskName $name
Write-Host "'$name' o'rnatildi va ishga tushirildi: http://localhost:5173"
