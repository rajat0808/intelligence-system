$ErrorActionPreference = "Stop"

$processes = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -eq "python.exe" -and $_.CommandLine -like "*uvicorn app.main:app*"
}

if (-not $processes) {
    Write-Host "No app.main Uvicorn process is running."
    exit 0
}

foreach ($proc in $processes) {
    try {
        Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop
        Write-Host "Stopped process $($proc.ProcessId)"
    }
    catch {
        Write-Host "Could not stop process $($proc.ProcessId): $($_.Exception.Message)"
    }
}
