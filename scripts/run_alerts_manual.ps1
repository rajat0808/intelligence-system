param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [Nullable[bool]]$SendNotifications = $null,
    [Nullable[bool]]$SendPdfToTelegram = $null,
    [switch]$NoNotifications,
    [switch]$NoPdfTelegram,
    [switch]$PdfOnly,
    [switch]$ForceResend,
    [switch]$ResetTodayQuota
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

function Read-DotEnvValues {
    param([string]$Path)

    $values = @{}
    if (-not (Test-Path $Path)) {
        return $values
    }

    foreach ($rawLine in Get-Content $Path) {
        $line = $rawLine.Trim()
        if (-not $line -or $line.StartsWith("#")) {
            continue
        }

        $separatorIndex = $line.IndexOf("=")
        if ($separatorIndex -le 0) {
            continue
        }

        $name = $line.Substring(0, $separatorIndex).Trim()
        if (-not $name) {
            continue
        }

        $value = $line.Substring($separatorIndex + 1)
        if ($value.Length -ge 2) {
            $first = $value[0]
            $last = $value[$value.Length - 1]
            if (($first -eq '"' -and $last -eq '"') -or ($first -eq "'" -and $last -eq "'")) {
                $value = $value.Substring(1, $value.Length - 2)
            }
        }

        $values[$name] = $value
    }

    return $values
}

function Get-SettingValue {
    param(
        [string]$Name,
        [hashtable]$DotEnv,
        [string]$Default = ""
    )

    $envValue = (Get-Item -Path "Env:$Name" -ErrorAction SilentlyContinue).Value
    if (-not [string]::IsNullOrWhiteSpace($envValue)) {
        return $envValue.Trim()
    }

    if ($DotEnv.ContainsKey($Name)) {
        return [string]$DotEnv[$Name]
    }

    return $Default
}

function ConvertTo-Bool {
    param(
        [string]$Value,
        [bool]$Default = $false
    )

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return $Default
    }

    $normalized = $Value.Trim().ToLowerInvariant()
    if ($normalized -in @("1", "true", "yes", "on")) {
        return $true
    }
    if ($normalized -in @("0", "false", "no", "off")) {
        return $false
    }

    return $Default
}

function Reset-TodayPdfQuotaFiles {
    param([string]$RootPath)

    $dateTag = Get-Date -Format "yyyyMMdd"
    $pattern = "daily_alert_report_${dateTag}_*.pdf"
    $todayReports = @(Get-ChildItem -Path $RootPath -Filter $pattern -File -ErrorAction SilentlyContinue)

    if (-not $todayReports) {
        Write-Host "No existing report files found for $dateTag."
        return
    }

    $archiveDir = Join-Path (Join-Path $RootPath "reports_archive") ("manual_reset_{0}" -f (Get-Date -Format "yyyyMMdd_HHmmss"))
    New-Item -Path $archiveDir -ItemType Directory -Force | Out-Null

    foreach ($report in $todayReports) {
        $destination = Join-Path $archiveDir $report.Name
        Move-Item -Path $report.FullName -Destination $destination -Force
    }

    Write-Host ("Archived {0} report(s) to {1}" -f $todayReports.Count, $archiveDir)
}

function Test-ServerHealth {
    param([string]$Url)

    $healthUrl = "{0}/health" -f $Url.TrimEnd("/")
    try {
        Invoke-RestMethod -Method Get -Uri $healthUrl -TimeoutSec 15 | Out-Null
    }
    catch {
        $message = $_.Exception.Message
        throw "Server is not reachable at $healthUrl. Start it first with scripts/start_server.ps1. Details: $message"
    }
}

if ($ResetTodayQuota.IsPresent) {
    Reset-TodayPdfQuotaFiles -RootPath $repoRoot
}

$dotEnv = Read-DotEnvValues -Path (Join-Path $repoRoot ".env")
$apiKey = Get-SettingValue -Name "FOUNDER_API_KEY" -DotEnv $dotEnv
$apiKeyHeader = Get-SettingValue -Name "API_KEY_HEADER" -DotEnv $dotEnv -Default "X-API-Key"

Test-ServerHealth -Url $BaseUrl

$sendNotificationsValue = $true
if ($NoNotifications.IsPresent) {
    $sendNotificationsValue = $false
}
elseif ($null -ne $SendNotifications) {
    $sendNotificationsValue = [bool]$SendNotifications
}
else {
    $alertPdfOnly = Get-SettingValue -Name "ALERT_PDF_ONLY" -DotEnv $dotEnv
    $sendNotificationsValue = -not (ConvertTo-Bool -Value $alertPdfOnly -Default $false)
}

$sendPdfToTelegramValue = $true
if ($NoPdfTelegram.IsPresent) {
    $sendPdfToTelegramValue = $false
}
elseif ($null -ne $SendPdfToTelegram) {
    $sendPdfToTelegramValue = [bool]$SendPdfToTelegram
}

$headers = @{}
if (-not [string]::IsNullOrWhiteSpace($apiKey)) {
    $headers["X-API-Key"] = $apiKey
    $headers["api-key"] = $apiKey
    if (
        $apiKeyHeader -and
        $apiKeyHeader -ne "X-API-Key" -and
        $apiKeyHeader -ne "api-key"
    ) {
        $headers[$apiKeyHeader] = $apiKey
    }
}

$query = @{
    "send_pdf_to_telegram" = if ($sendPdfToTelegramValue) { "true" } else { "false" }
}

if (-not $PdfOnly.IsPresent) {
    $query["send_notifications"] = if ($sendNotificationsValue) { "true" } else { "false" }
    $query["force_resend"] = if ($ForceResend.IsPresent) { "true" } else { "false" }
    $query["generate_pdf_report"] = "true"
}

$queryString = ($query.GetEnumerator() | Sort-Object Name | ForEach-Object {
        "{0}={1}" -f $_.Key, $_.Value
    }) -join "&"

$endpointPath = if ($PdfOnly.IsPresent) { "/alerts/report/run" } else { "/alerts/run" }
$runUrl = "{0}{1}?{2}" -f $BaseUrl.TrimEnd("/"), $endpointPath, $queryString

Write-Host "Triggering alert workflow at $runUrl"

try {
    $response = Invoke-RestMethod -Method Post -Uri $runUrl -Headers $headers -TimeoutSec 300
}
catch {
    $details = $_.Exception.Message
    if ($_.ErrorDetails -and $_.ErrorDetails.Message) {
        $details = $_.ErrorDetails.Message
    }
    Write-Error "Manual alert trigger failed: $details"
    exit 1
}

$stats = $response.stats
$report = $response.report

$statusValue = "unknown"
if ($response -and $null -ne $response.status -and ([string]$response.status) -ne "") {
    $statusValue = [string]$response.status
}

$snapshotsValue = 0
$alertsValue = 0
if ($stats) {
    if ($null -ne $stats.snapshots) {
        $snapshotsValue = [int]$stats.snapshots
    }
    if ($null -ne $stats.alerts) {
        $alertsValue = [int]$stats.alerts
    }
}

Write-Host ("Status: {0}" -f $statusValue)
Write-Host ("Snapshots processed: {0}" -f $snapshotsValue)
Write-Host ("Alerts logged: {0}" -f $alertsValue)
if ($null -ne $report) {
    $generatedReports = 0
    $existingReports = 0
    if ($null -ne $report.generated_reports) {
        $generatedReports = [int]$report.generated_reports
    }
    if ($null -ne $report.existing_reports_today) {
        $existingReports = [int]$report.existing_reports_today
    }

    Write-Host ("Generated PDFs this run: {0}" -f $generatedReports)
    Write-Host ("Existing PDFs today: {0}" -f $existingReports)
    if ($report.skipped_reason) {
        Write-Host ("Report note: {0}" -f $report.skipped_reason)
    }
    $reportItems = @()
    if ($report.reports) {
        $reportItems = @($report.reports)
    }
    foreach ($reportItem in $reportItems) {
        Write-Host ("Report #{0}: {1}" -f $reportItem.report_index, $reportItem.path)
    }
}

$response | ConvertTo-Json -Depth 8
