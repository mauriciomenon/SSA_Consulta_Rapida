# Shared environment bootstrap for SSA_Consulta_Rapida (PowerShell version)
# Compatible with direnv_common.sh logic but adapted for Windows PowerShell

# Validate the native host before honoring recursion guards or touching an environment.
$ssaRepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
. (Join-Path $PSScriptRoot 'native_host_guard.ps1')
Assert-SsaWindowsHost -RepoRoot $ssaRepoRoot -ExpectedRoot (Get-SsaWindowsRepoRoot)
Assert-SsaWindowsVenv -VenvDir (Join-Path $ssaRepoRoot '.venv')
Assert-SsaWindowsVenv -VenvDir (Join-Path $ssaRepoRoot '.venv_ft')

# Prevent recursive sourcing
if (${env:SSA_ENV_COMMON_SOURCED}) {
    return 0
}
$env:SSA_ENV_COMMON_SOURCED = "1"

# Set repository root from this script, never from the caller's working directory.
$env:SSA_ENV_REPO_ROOT = $ssaRepoRoot

# Python version configuration
if (-not $env:SSA_PYTHON_STABLE_VERSION) {
    $env:SSA_ENV__STABLE_FROM_ENV = 0
} else {
    $env:SSA_ENV__STABLE_FROM_ENV = 1
}

$env:SSA_PYTHON_STABLE_VERSION = if ($env:SSA_PYTHON_STABLE_VERSION) { $env:SSA_PYTHON_STABLE_VERSION } else { "3.13.12" }

if ($env:SSA_ENV__STABLE_FROM_ENV -eq 0 -and (Test-Path "$env:SSA_ENV_REPO_ROOT\.python-version")) {
    try {
        $fileVersion = Get-Content "$env:SSA_ENV_REPO_ROOT\.python-version" -Raw
        $env:SSA_ENV__FILE_VERSION = $fileVersion.Trim().TrimEnd("`r")
        $pythonVersionPattern = '^\d+\.\d+(\.\d+)?$'
        if ($env:SSA_ENV__FILE_VERSION -match $pythonVersionPattern) {
            $env:SSA_PYTHON_STABLE_VERSION = $env:SSA_ENV__FILE_VERSION
        }
    } catch {
        # Ignore errors reading file
    }
}
Remove-Variable -Name SSA_ENV__STABLE_FROM_ENV -ErrorAction SilentlyContinue
Remove-Variable -Name SSA_ENV__FILE_VERSION -ErrorAction SilentlyContinue

$env:SSA_PYTHON_FT_VERSION = if ($env:SSA_PYTHON_FT_VERSION) { $env:SSA_PYTHON_FT_VERSION } else { "3.14-dev" }

function ssa_env__log {
    param([string]$Message)
    Write-Output "[env] $Message"
}

function ssa_env__sanitize_for_name {
    param([string]$Raw)
    $lowered = $Raw.ToLower()
    $sanitized = $lowered -replace '[^a-z0-9]+', '_' -replace '^_+', '' -replace '_+$', ''
    return $sanitized
}

function ssa_env__determine_variant {
    $requested = if ($env:SSA_PYTHON_VARIANT) { $env:SSA_PYTHON_VARIANT } else { "" }

    if ($env:SSA_USE_FREE_THREADED -and $env:SSA_USE_FREE_THREADED -ne "0") {
        $requested = "free-threaded"
    }

    switch ($requested) {
        { $_ -in @("", "default", "stable", "prod", "production") } {
            $env:SSA_ENV_VARIANT = "stable"
            $env:SSA_ENV_PY_VERSION = $env:SSA_PYTHON_STABLE_VERSION
            $env:SSA_ENV_VENV_DIR = ".venv"
        }
        { $_ -in @("ft", "free-threaded", "free_threaded", "free") } {
            $env:SSA_ENV_VARIANT = "free-threaded"
            $env:SSA_ENV_PY_VERSION = $env:SSA_PYTHON_FT_VERSION
            $env:SSA_ENV_VENV_DIR = ".venv_ft"
        }
        default {
            ssa_env__log "note: unknown SSA_PYTHON_VARIANT '$requested', using stable"
            $env:SSA_ENV_VARIANT = "stable"
            $env:SSA_ENV_PY_VERSION = $env:SSA_PYTHON_STABLE_VERSION
            $env:SSA_ENV_VENV_DIR = ".venv"
        }
    }

    if ($env:SSA_VENV_DIR_OVERRIDE) {
        if ($env:SSA_VENV_DIR_OVERRIDE -notmatch '^\.venv[_A-Za-z0-9.-]*$') {
            throw 'SSA_VENV_DIR_OVERRIDE must be a .venv name inside the repository'
        }
        $env:SSA_ENV_VENV_DIR = $env:SSA_VENV_DIR_OVERRIDE
    }

    $sanitized = ssa_env__sanitize_for_name $env:SSA_ENV_PY_VERSION
    if (-not $sanitized) {
        $sanitized = "python"
    }
    $env:SSA_ENV_PYENV_NAME = "ssa_consulta_$($env:SSA_ENV_VARIANT)_$sanitized"
}

function ssa_env__init_pyenv {
    if ($env:SSA_SKIP_PYENV -eq "1") {
        $env:SSA_ENV_PYENV_INITIALIZED = "1"
        $env:SSA_ENV_PYENV_AVAILABLE = "0"
        $env:SSA_ENV_PYENV_HAS_VIRTUALENV = "0"
        return $false
    }

    if ($env:SSA_ENV_PYENV_INITIALIZED -eq "1") {
        return ($env:SSA_ENV_PYENV_AVAILABLE -eq "1")
    }

    $env:SSA_ENV_PYENV_INITIALIZED = "1"

    try {
        $null = Get-Command pyenv -ErrorAction Stop
        $env:SSA_ENV_PYENV_AVAILABLE = "1"

        # Check if virtualenv command is available
        try {
            $null = pyenv commands 2>$null | Select-String "virtualenv"
            $env:SSA_ENV_PYENV_HAS_VIRTUALENV = "1"
        } catch {
            $env:SSA_ENV_PYENV_HAS_VIRTUALENV = "0"
        }

        return $true
    } catch {
        $env:SSA_ENV_PYENV_AVAILABLE = "0"
        $env:SSA_ENV_PYENV_HAS_VIRTUALENV = "0"
        return $false
    }
}

function ssa_env__ensure_pyenv_env {
    if ($env:SSA_ENV_PYENV_AVAILABLE -ne "1") {
        return $false
    }

    $version = $env:SSA_ENV_PY_VERSION
    $envName = $env:SSA_ENV_PYENV_NAME

    # Check if version is installed
    try {
        $installedVersions = pyenv versions --bare 2>$null
        if ($installedVersions -notcontains $version) {
            ssa_env__log "pyenv: installing Python $version (first run may take a while)"
            if ($LASTEXITCODE -ne 0) {
                pyenv install $version
                if ($LASTEXITCODE -ne 0) {
                    ssa_env__log "error: pyenv install $version failed"
                    return $false
                }
            }
        }
    } catch {
        ssa_env__log "error: pyenv install $version failed"
        return $false
    }

    if ($env:SSA_ENV_PYENV_HAS_VIRTUALENV -eq "1") {
        # Create/activate virtualenv
        try {
            $virtualenvs = pyenv virtualenvs --bare 2>$null
            if ($virtualenvs -notcontains $envName) {
                ssa_env__log "pyenv: creating virtualenv $envName"
                pyenv virtualenv $version $envName
                if ($LASTEXITCODE -ne 0) {
                    ssa_env__log "error: pyenv virtualenv $envName failed"
                    return $false
                }
            }

            pyenv activate $envName 2>$null
            if ($LASTEXITCODE -eq 0) {
                $env:SSA_ENV_SOURCE = "pyenv-virtualenv"
            } else {
                ssa_env__log "error: pyenv activate $envName failed"
                return $false
            }
        } catch {
            ssa_env__log "error: pyenv virtualenv setup failed"
            return $false
        }
    } else {
        # Use pyenv local instead of shell to avoid session pollution
        try {
            pyenv local $version 2>$null
            if ($LASTEXITCODE -eq 0) {
                # Ensure no session override remains
                try { pyenv shell --unset 2>$null } catch {}
                Remove-Item Env:PYENV_VERSION -ErrorAction SilentlyContinue
                # Let pyenv manage version via .python-version
                $env:SSA_ENV_SOURCE = "pyenv-local"
            } else {
                ssa_env__log "error: pyenv local $version failed"
                return $false
            }
        } catch {
            ssa_env__log "error: pyenv local $version failed"
            return $false
        }
    }

    return $true
}

function ssa_env__activate_local_venv {
    $dir = Join-Path $env:SSA_ENV_REPO_ROOT $env:SSA_ENV_VENV_DIR
    Assert-SsaWindowsVenv -VenvDir $dir
    $pythonCmd = if ($env:SSA_ENV_FALLBACK_PYTHON) { $env:SSA_ENV_FALLBACK_PYTHON } else { "python3" }

    try {
        $null = Get-Command $pythonCmd -ErrorAction Stop
    } catch {
        $pythonCmd = "python"
        try {
            $null = Get-Command $pythonCmd -ErrorAction Stop
        } catch {
            ssa_env__log "error: python interpreter not found for fallback venv"
            return $false
        }
    }

    if (-not (Test-Path $dir)) {
        if ($env:SSA_ENV_VARIANT -eq "free-threaded") {
            ssa_env__log "warn: free-threaded variant requested but pyenv unavailable; using fallback venv $dir"
        } else {
            ssa_env__log "creating fallback venv $dir"
        }

        try {
            & $pythonCmd -m venv $dir
            if ($LASTEXITCODE -ne 0) {
                ssa_env__log "error: failed to create venv $dir"
                return $false
            }
        } catch {
            ssa_env__log "error: failed to create venv $dir"
            return $false
        }
    }

    # Ensure pip is available in venv before activation
    if (-not (ssa_env__ensure_venv_pip $dir)) {
        return $false
    }

    # Windows has Scripts\activate.ps1, Unix has bin/activate
    $activateScript = if (Test-Path "$dir\Scripts\Activate.ps1") { "$dir\Scripts\Activate.ps1" } elseif (Test-Path "$dir\bin\activate") { "$dir\bin\activate" } else { ssa_env__log "error: activate script missing in $dir"; return $false }

    try {
        . $activateScript
        $env:SSA_ENV_SOURCE = "venv"
        return $true
    } catch {
        ssa_env__log "error: failed to activate venv $dir"
        return $false
    }
}

function ssa_env__ensure_venv_pip {
    param([string]$dir)

    $venvPython = if (Test-Path "$dir\Scripts\python.exe") {
        "$dir\Scripts\python.exe"
    } elseif (Test-Path "$dir\bin\python") {
        "$dir\bin\python"
    } else {
        ssa_env__log "error: python executable missing in $dir"
        return $false
    }

    try {
        & $venvPython -m pip --version *> $null
        if ($LASTEXITCODE -eq 0) {
            return $true
        }
    } catch {
        # continue to ensurepip bootstrap
    }

    ssa_env__log "venv: pip missing in $dir; bootstrapping with ensurepip"
    try {
        & $venvPython -m ensurepip --upgrade *> $null
        if ($LASTEXITCODE -ne 0) {
            ssa_env__log "error: failed to bootstrap pip in $dir"
            return $false
        }
    } catch {
        ssa_env__log "error: failed to bootstrap pip in $dir"
        return $false
    }

    try {
        & $venvPython -m pip --version *> $null
        if ($LASTEXITCODE -eq 0) {
            return $true
        }
    } catch {
        # continue to final error
    }

    ssa_env__log "error: pip still unavailable in $dir after ensurepip"
    return $false
}

function ssa_env__apply_path_exports {
    $env:PYTHONUTF8 = "1"
    $env:PYTHONDONTWRITEBYTECODE = "1"

    if (-not $env:SSA_ENV_PATH_APPLIED) {
        $currentPath = $env:PATH
        $env:PATH = "$env:SSA_ENV_REPO_ROOT\scripts;$env:SSA_ENV_REPO_ROOT\scripts_manutencao;$currentPath"
        $env:SSA_ENV_PATH_APPLIED = "1"
    }

    $env:SSA_ENV_ACTIVE = "1"
}

function ssa_env__print_summary {
    $context = $args[0]

    try {
        $pyVersion = & python --version 2>&1
        $pyVersion = $pyVersion -replace 'Python\s+', ''
    } catch {
        $pyVersion = "unknown"
    }

    $sourceNote = $env:SSA_ENV_SOURCE
    if ($env:SSA_ENV_SOURCE -eq "pyenv-virtualenv") {
        $sourceNote = "pyenv-virtualenv:$($env:SSA_ENV_PYENV_NAME)"
    } elseif ($env:SSA_ENV_SOURCE -eq "pyenv-local") {
        $sourceNote = "pyenv-local:$($env:SSA_ENV_PY_VERSION)"
    } elseif ($env:SSA_ENV_SOURCE -eq "venv") {
        $sourceNote = "venv:$($env:SSA_ENV_VENV_DIR)"
    }

    ssa_env__log "python $pyVersion ($($env:SSA_ENV_VARIANT) via $sourceNote)"

    if ($env:SSA_ENV_VARIANT -eq "free-threaded" -and $env:SSA_ENV_SOURCE -ne "pyenv-virtualenv") {
        ssa_env__log "note: fallback environment may not have free-threaded build"
    }

    if ($context -eq "direnv") {
        ssa_env__log "direnv ready (run 'direnv allow' after changing this file)"
    }
}

function ssa_env_apply {
    $context = if ($args[0]) { $args[0] } else { "direnv" }

    if (-not $env:DIRENV_LOG_FORMAT) {
        $env:DIRENV_LOG_FORMAT = "[direnv] %s"
    }

    ssa_env__determine_variant
    $env:UV_PYTHON = $env:SSA_ENV_PY_VERSION
    $env:UV_PROJECT_ENVIRONMENT = Join-Path $env:SSA_ENV_REPO_ROOT $env:SSA_ENV_VENV_DIR
    $usedPyenv = $false

    if (ssa_env__init_pyenv) {
        if (ssa_env__ensure_pyenv_env) {
            $usedPyenv = $true
        } else {
            ssa_env__log "warn: pyenv setup failed; falling back to local venv"
        }
    }

    if (-not $usedPyenv) {
        if (-not (ssa_env__activate_local_venv)) {
            return $false
        }
    }

    ssa_env__apply_path_exports
    ssa_env__print_summary $context
    return $true
}

# Export functions for bash compatibility when sourced from .envrc
# For PowerShell, these are already defined as functions above
