param(
    [string]$BindAddress = "127.0.0.1",
    [int]$PreferredPort = 8000,
    [switch]$Reload
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

function Import-DotEnv {
    $envFile = Join-Path $repoRoot ".env"
    if (-not (Test-Path $envFile)) {
        return
    }

    foreach ($rawLine in Get-Content $envFile) {
        $line = $rawLine.Trim()
        if (-not $line -or $line.StartsWith("#")) {
            continue
        }

        $separatorIndex = $line.IndexOf("=")
        if ($separatorIndex -le 0) {
            continue
        }

        $name = $line.Substring(0, $separatorIndex).Trim()
        $value = $line.Substring($separatorIndex + 1)
        if ($value.Length -ge 2) {
            $first = $value[0]
            $last = $value[$value.Length - 1]
            if (($first -eq '"' -and $last -eq '"') -or ($first -eq "'" -and $last -eq "'")) {
                $value = $value.Substring(1, $value.Length - 2)
            }
        }

        [Environment]::SetEnvironmentVariable($name, $value, "Process")
    }
}

function Get-ListeningPorts {
    try {
        return @(Get-NetTCPConnection -State Listen -ErrorAction Stop | Select-Object -ExpandProperty LocalPort)
    }
    catch {
        return @()
    }
}

function Get-NextFreePort {
    param(
        [int]$StartPort,
        [int]$MaxPort = 8100
    )
    $listening = [System.Collections.Generic.HashSet[int]]::new()
    foreach ($port in (Get-ListeningPorts)) {
        [void]$listening.Add([int]$port)
    }
    for ($port = $StartPort; $port -le $MaxPort; $port++) {
        if (-not $listening.Contains($port)) {
            return $port
        }
    }
    return $null
}

function Stop-AppUvicornProcesses {
    $processes = Get-CimInstance Win32_Process | Where-Object {
        $_.Name -eq "python.exe" -and $_.CommandLine -like "*uvicorn app.main:app*"
    }
    foreach ($proc in $processes) {
        try {
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop
        }
        catch {
            # Ignore processes we cannot terminate; a free port will still be selected.
        }
    }
}

function Resolve-PythonPath {
    $candidates = @(
        ".venv\Scripts\python.exe",
        "venv\Scripts\python.exe",
        "python"
    )
    foreach ($candidate in $candidates) {
        if ($candidate -eq "python") {
            return $candidate
        }
        if (Test-Path $candidate) {
            return $candidate
        }
    }
    return "python"
}

Stop-AppUvicornProcesses
Import-DotEnv

$port = Get-NextFreePort -StartPort $PreferredPort
if ($null -eq $port) {
    throw "No free port found between $PreferredPort and 8100."
}

$pythonPath = Resolve-PythonPath
$args = @(
    "-m", "uvicorn",
    "app.main:app",
    "--host", $BindAddress,
    "--port", $port.ToString()
)
if ($Reload.IsPresent) {
    $args += "--reload"
}

Write-Host "Starting server on http://$BindAddress`:$port"
Write-Host "Scheduler and startup alerts run automatically."
Write-Host "Webhook URL: http://$BindAddress`:$port/whatsapp/webhook"

& $pythonPath @args
