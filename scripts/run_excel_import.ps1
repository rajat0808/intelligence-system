param(
    [string]$Workbook = (Join-Path $PSScriptRoot "..\\datasource\\daily_update.xlsx"),
    [string[]]$Sheets,
    [switch]$DryRun
)

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$python = Join-Path $repoRoot ".venv\\Scripts\\python.exe"
if (-not (Test-Path $python)) {
    $python = "python"
}

$scriptPath = Join-Path $repoRoot "scripts\\import_excel.py"
$argsList = @($scriptPath, "--path", $Workbook)
if ($Sheets) {
    $argsList += "--sheets"
    $argsList += $Sheets
}
if ($DryRun) {
    $argsList += "--dry-run"
}

& $python @argsList
exit $LASTEXITCODE
