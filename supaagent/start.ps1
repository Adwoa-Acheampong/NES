param(
  [switch]$StatusOnly,
  [switch]$DryRun,
  [string[]]$Only = @(),
  [string]$Config = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$Script = Join-Path $PSScriptRoot "start.py"

$ArgsList = @($Script)
if ($Config -ne "") {
  $ArgsList += @("--config", $Config)
}
if ($StatusOnly) {
  $ArgsList += "--status-only"
}
if ($DryRun) {
  $ArgsList += "--dry-run"
}
foreach ($Service in $Only) {
  $ArgsList += @("--only", $Service)
}

Push-Location $Root
try {
  python @ArgsList
}
finally {
  Pop-Location
}
