param(
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Path $PSScriptRoot -Parent | Split-Path -Parent
$sitePath = Join-Path $repoRoot "site"

if (-not (Test-Path $sitePath)) {
    throw "Site folder not found: $sitePath"
}

Push-Location $sitePath
try {
    Write-Host "Serving dashboard from $sitePath on http://127.0.0.1:$Port/"
    python -m http.server $Port
}
finally {
    Pop-Location
}