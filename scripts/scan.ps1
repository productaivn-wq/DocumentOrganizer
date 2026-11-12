# scan.ps1
# Usage: .\scan.ps1 -Root "C:\path\to\target" [-LargeFileMB 50] [-ExcludePatterns @(".git","node_modules")]
# Outputs: anomaly report (empty folders, large files, duplicates by name+size)

param(
    [Parameter(Mandatory=$true)]
    [string]$Root,
    [int]$LargeFileMB = 50,
    [string[]]$ExcludePatterns = @(".git", "node_modules", "__pycache__", '$RECYCLE.BIN', "System Volume Information")
)

Write-Host "`n=== SCAN: $Root ===" -ForegroundColor Cyan

# Build exclude filter
$excludeRegex = ($ExcludePatterns | ForEach-Object { [regex]::Escape($_) }) -join '|'

# 1. Total file count (excluding patterns)
$allFiles = Get-ChildItem -LiteralPath $Root -Recurse -File -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notmatch $excludeRegex }
Write-Host "Total files: $($allFiles.Count)"

# 2. Top-level structure
Write-Host "`n--- Top-level folders ---"
Get-ChildItem -LiteralPath $Root | Format-Table Name, @{N='Type';E={if($_.PSIsContainer){'DIR'}else{'FILE'}}}, @{N='Files';E={if($_.PSIsContainer){(Get-ChildItem -LiteralPath $_.FullName -Recurse -File -ErrorAction SilentlyContinue | Where-Object { $_.FullName -notmatch $excludeRegex }).Count}else{'-'}}} -AutoSize

# 3. Large files
Write-Host "`n--- Files > ${LargeFileMB}MB ---"
$allFiles | Where-Object { $_.Length -gt ($LargeFileMB * 1MB) } | Sort-Object Length -Descending | Select-Object @{N='Size(MB)';E={[Math]::Round($_.Length/1MB,1)}}, FullName | Format-Table -AutoSize

# 4. Empty folders
Write-Host "`n--- Empty folders ---"
Get-ChildItem -LiteralPath $Root -Recurse -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notmatch $excludeRegex } |
    Where-Object {
        (Get-ChildItem -LiteralPath $_.FullName -Recurse -File -ErrorAction SilentlyContinue).Count -eq 0
    } | Select-Object FullName | Format-Table -AutoSize

# 5. Duplicates (same name + size)
Write-Host "`n--- Potential duplicates (same name + size) ---"
$allFiles | Group-Object { "$($_.Name)|$($_.Length)" } | Where-Object { $_.Count -gt 1 } | ForEach-Object {
    Write-Host "  DUPLICATE ($($_.Count)x): $($_.Name.Split('|')[0])"
    $_.Group | ForEach-Object { Write-Host "    $($_.FullName)" }
}

Write-Host "`nScan complete." -ForegroundColor Green
