# append_profile_snippet.ps1
$ts = Get-Date -Format 'yyyyMMddHHmmss'
$backup = $PROFILE + '.bak.' + $ts
if (Test-Path $PROFILE) {
    Copy-Item $PROFILE $backup -Force
    Write-Host "Profile backed up to $backup"
} else {
    New-Item -Path $PROFILE -ItemType File -Force | Out-Null
    Write-Host "Profile file created at $PROFILE"
}
$snippet = @'
# Auto-source project activation helper when in the project path
$repoRoot = 'C:\Users\menon\git\SSA_Consulta_Rapida'
if ($PWD.Path -like "$repoRoot*") {
    $helper = Join-Path $repoRoot 'activate_repo.ps1'
    if (Test-Path $helper) {
        . $helper
    }
}
'@
Add-Content -Path $PROFILE -Value $snippet -Encoding utf8
Write-Host "Snippet appended to $PROFILE"

# Source the profile in this session and test environment
. $PROFILE
Write-Host '---ENV AFTER PROFILE---'
Write-Host "PYTHONUTF8=$env:PYTHONUTF8"
if ($env:PATH -match 'scripts') { Write-Host 'PATH contains scripts' } else { Write-Host 'PATH does NOT contain scripts' }
