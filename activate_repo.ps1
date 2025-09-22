# activate_repo.ps1
# Small helper to replicate the effects of .envrc on Windows PowerShell
# Usage: .\activate_repo.ps1   (dot-source to keep env vars in current session)

# Activate .venv if present
if (Test-Path -Path '.venv\Scripts\Activate.ps1') {
    . '.\.venv\Scripts\Activate.ps1'
} elseif (Test-Path -Path '.python-version') {
    # If pyenv-win is installed, try to activate the pyenv virtualenv name
    $pyenv = Get-Command pyenv -ErrorAction SilentlyContinue
    if ($pyenv) {
        $venvName = Get-Content .python-version -Raw
        $venvName = $venvName.Trim()
        try {
            pyenv activate $venvName | Out-Null
        } catch {
            Write-Host "pyenv activate failed or pyenv-win not configured: $_"
        }
    }
}

# Set common env vars
$env:PYTHONUTF8 = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'

# Prepend scripts folders to PATH (project-local)
$project = (Get-Location).Path
$scriptsPath = Join-Path $project 'scripts'
$scriptsManPath = Join-Path $project 'scripts_manutencao'
if (Test-Path $scriptsPath) { $env:PATH = "$scriptsPath;$env:PATH" }
if (Test-Path $scriptsManPath) { $env:PATH = "$scriptsManPath;$env:PATH" }

Write-Host "[activate_repo] Env applied. Virtual env: $($env:VIRTUAL_ENV)"
