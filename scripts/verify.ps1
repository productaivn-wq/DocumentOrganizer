# verify.ps1
# Usage: .\verify.ps1 -Root "C:\path\to\target" [-CheckPaths @("path1","path2")]
# Returns: file count + pass/fail on expected paths

param(
    [Parameter(Mandatory=$true)]
    [string]$Root,
    [string[]]$CheckPaths = @()
)

$count = (Get-ChildItem -LiteralPath $Root -Recurse -File -ErrorAction SilentlyContinue).Count
Write-Host "File count: $count"

foreach ($p in $CheckPaths) {
    $fullPath = if ([System.IO.Path]::IsPathRooted($p)) { $p } else { Join-Path $Root $p }
    $exists = Test-Path -LiteralPath $fullPath
    $icon = if ($exists) { "OK" } else { "MISSING" }
    Write-Host "  [$icon] $fullPath"
}
