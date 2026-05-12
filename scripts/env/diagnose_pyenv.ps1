# Diagnostic script to find where pyenv 3.14.0 is being set

Write-Host "=== DIAGNOSTIC: pyenv version forcing ===" -ForegroundColor Cyan
Write-Host ""

# Check environment variables
Write-Host "Environment Variables:" -ForegroundColor Yellow
$vars = @('PYENV_VERSION', 'SSA_USE_FREE_THREADED', 'SSA_PYTHON_VARIANT', 'SSA_PYTHON_FT_VERSION')
foreach ($var in $vars) {
    $val = [Environment]::GetEnvironmentVariable($var)
    if ($val) {
        Write-Host "  $var = $val" -ForegroundColor Red
    } else {
        Write-Host "  $var = (not set)" -ForegroundColor Green
    }
}

# Check pyenv configuration
Write-Host ""
Write-Host "PyEnv Configuration:" -ForegroundColor Yellow
if (Get-Command pyenv -ErrorAction SilentlyContinue) {
    Write-Host "  pyenv version: $(pyenv --version)" -ForegroundColor Green
    Write-Host "  pyenv shell: $(pyenv shell 2>&1)" -ForegroundColor Cyan
    
    $repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
    $pyVersionFile = Join-Path $repoRoot ".python-version"
    if (Test-Path $pyVersionFile) {
        $version = Get-Content $pyVersionFile | % Trim
        Write-Host "  .python-version: $version" -ForegroundColor Cyan
    }
    
    $pyenvLocal = Join-Path $repoRoot ".pyenv-local"
    if (Test-Path $pyenvLocal) {
        Write-Host "  .pyenv-local exists (OLD, should use .python-version)" -ForegroundColor Red
    }
} else {
    Write-Host "  pyenv: NOT FOUND" -ForegroundColor Red
}

# Check .pyenv root
Write-Host ""
Write-Host "PyEnv Root Configuration:" -ForegroundColor Yellow
$pyenvRoot = $env:PYENV_ROOT
if (-not $pyenvRoot) {
    $pyenvRoot = "$env:USERPROFILE\.pyenv\pyenv-win"
    if (-not (Test-Path $pyenvRoot)) {
        $pyenvRoot = "$env:USERPROFILE\.pyenv"
    }
}
Write-Host "  PYENV_ROOT: $pyenvRoot" -ForegroundColor Cyan

if (Test-Path "$pyenvRoot\.python-version") {
    $version = Get-Content "$pyenvRoot\.python-version" | % Trim
    Write-Host "  Global .python-version: $version (WARNING: should use repo-level)" -ForegroundColor Yellow
}

# Check shell history for pyenv shell commands
Write-Host ""
Write-Host "PowerShell History (last 30 commands):" -ForegroundColor Yellow
$history = Get-History -Count 30 -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*pyenv*" }
if ($history) {
    foreach ($h in $history) {
        Write-Host "  > $($h.CommandLine)" -ForegroundColor Cyan
    }
} else {
    Write-Host "  (no pyenv commands in recent history)" -ForegroundColor Green
}

# Recommendations
Write-Host ""
Write-Host "FIXES:" -ForegroundColor Green
Write-Host "1. Clear session variables:"
Write-Host "   Remove-Item Env:PYENV_VERSION -ErrorAction SilentlyContinue"
Write-Host "   Remove-Item Env:SSA_USE_FREE_THREADED -ErrorAction SilentlyContinue"
Write-Host "   Remove-Item Env:SSA_PYTHON_VARIANT -ErrorAction SilentlyContinue"
Write-Host ""
Write-Host "2. Clear global pyenv setting (if exists):"
Write-Host "   Remove-Item '$pyenvRoot\.python-version' -ErrorAction SilentlyContinue"
Write-Host ""
Write-Host "3. Verify repo .python-version is correct:"
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Write-Host "   Get-Content '$repoRoot\.python-version'"
Write-Host ""
Write-Host "4. Clear pyenv shell:"
Write-Host "   pyenv shell --unset"
Write-Host ""
