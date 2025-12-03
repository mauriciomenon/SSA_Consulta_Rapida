[CmdletBinding()]
param(
    [string]$Variant
)

function Write-EnvLog {
    param([string]$Message)
    Write-Host "[env] $Message"
}

function Sanitize-ForName {
    param([string]$Value)
    if (-not $Value) { return 'python' }
    $result = $Value.ToLowerInvariant()
    $result = $result -replace '[^a-z0-9]+', '_'
    $result = $result.Trim('_')
    if (-not $result) { $result = 'python' }
    return $result
}

function Invoke-Python {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    if (Get-Command python -ErrorAction SilentlyContinue) {
        & python @Args
        return $LASTEXITCODE
    }
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3 @Args
        return $LASTEXITCODE
    }
    throw "Python interpreter not found on PATH"
}

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $repoRoot) {
    $repoRoot = (Get-Location).Path
}

$requestedVariant = if ($Variant) {
    $Variant
} elseif ($env:SSA_USE_FREE_THREADED -and $env:SSA_USE_FREE_THREADED -ne '0') {
    'free-threaded'
} elseif ($env:SSA_PYTHON_VARIANT) {
    $env:SSA_PYTHON_VARIANT
} else {
    'stable'
}

$stableVersion = if ($env:SSA_PYTHON_STABLE_VERSION) { $env:SSA_PYTHON_STABLE_VERSION } else { '3.13.7' }
$ftVersion = if ($env:SSA_PYTHON_FT_VERSION) { $env:SSA_PYTHON_FT_VERSION } else { '3.14-dev' }

switch ($requestedVariant.ToLowerInvariant()) {
    '' { $variant = 'stable'; $targetVersion = $stableVersion; $venvDir = '.venv' }
    'stable' { $variant = 'stable'; $targetVersion = $stableVersion; $venvDir = '.venv' }
    'prod' { $variant = 'stable'; $targetVersion = $stableVersion; $venvDir = '.venv' }
    'production' { $variant = 'stable'; $targetVersion = $stableVersion; $venvDir = '.venv' }
    'default' { $variant = 'stable'; $targetVersion = $stableVersion; $venvDir = '.venv' }
    'ft' { $variant = 'free-threaded'; $targetVersion = $ftVersion; $venvDir = '.venv_ft' }
    'free-threaded' { $variant = 'free-threaded'; $targetVersion = $ftVersion; $venvDir = '.venv_ft' }
    'free_threaded' { $variant = 'free-threaded'; $targetVersion = $ftVersion; $venvDir = '.venv_ft' }
    'free' { $variant = 'free-threaded'; $targetVersion = $ftVersion; $venvDir = '.venv_ft' }
    default {
        Write-EnvLog "unknown variant '$requestedVariant', using stable"
        $variant = 'stable'
        $targetVersion = $stableVersion
        $venvDir = '.venv'
    }
}

$pyenvEnvName = "ssa_consulta_{0}_{1}" -f ($variant -replace '-', '_'), (Sanitize-ForName -Value $targetVersion)
$envSource = $null

$pyenv = Get-Command pyenv -ErrorAction SilentlyContinue
$pyenvAvailable = $false
$pyenvHasVirtualenv = $false
if ($pyenv) {
    $pyenvAvailable = $true
    try {
        $init = (pyenv init -) 2>$null
        if ($init) { Invoke-Expression $init }
    } catch {}
    try {
        $commands = pyenv commands
        if ($commands -match '(?m)^virtualenv$') {
            $pyenvHasVirtualenv = $true
            $virt = (pyenv virtualenv-init -) 2>$null
            if ($virt) { Invoke-Expression $virt }
        }
    } catch {
        $pyenvAvailable = $false
    }
}

if ($pyenvAvailable) {
    try {
        $versions = (pyenv versions --bare) 2>$null
        $versionList = @()
        if ($versions) { $versionList = $versions -split "`n" }
        if (-not ($versionList -contains $targetVersion)) {
            Write-EnvLog "pyenv: installing Python $targetVersion (first run may take a while)"
            pyenv install $targetVersion | Out-Null
        }
        if ($pyenvHasVirtualenv) {
            $venvs = (pyenv virtualenvs --bare) 2>$null
            $venvList = @()
            if ($venvs) { $venvList = $venvs -split "`n" }
            if (-not ($venvList -contains $pyenvEnvName)) {
                Write-EnvLog "pyenv: creating virtualenv $pyenvEnvName"
                pyenv virtualenv $targetVersion $pyenvEnvName | Out-Null
            }
            pyenv activate $pyenvEnvName | Out-Null
            $envSource = "pyenv-virtualenv:$pyenvEnvName"
        } else {
            pyenv shell $targetVersion | Out-Null
            $envSource = "pyenv:$targetVersion"
        }
    } catch {
        Write-EnvLog ("warn: pyenv setup failed; falling back to local venv ({0})" -f $_)
        $envSource = $null
    }
}

if (-not $envSource) {
    $venvPath = Join-Path $repoRoot $venvDir
    $activatePath = Join-Path $venvPath 'Scripts/Activate.ps1'
    if (-not (Test-Path $activatePath)) {
        if ($variant -eq 'free-threaded') {
            Write-EnvLog "warn: free-threaded variant requested but pyenv unavailable; creating fallback venv $venvDir"
        } else {
            Write-EnvLog "creating fallback venv $venvDir"
        }
        $result = Invoke-Python -Args @('-m', 'venv', $venvPath)
        if ($result -ne 0) {
            throw "Failed to create fallback venv $venvPath"
        }
    }
    . $activatePath
    $envSource = "venv:$venvDir"
}

$env:PYTHONUTF8 = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:SSA_ENV_ACTIVE = '1'
$env:SSA_ENV_VARIANT = $variant
$env:SSA_ENV_PYTHON_VERSION = $targetVersion
$env:SSA_ENV_SOURCE = $envSource
$env:SSA_ENV_ROOT = $repoRoot

$scriptPath = Join-Path $repoRoot 'scripts'
$maintPath = Join-Path $repoRoot 'scripts_manutencao'
$existingPaths = $env:PATH -split ';'
foreach ($path in @($scriptPath, $maintPath)) {
    if ((Test-Path $path) -and (-not ($existingPaths -contains $path))) {
        $env:PATH = "$path;$env:PATH"
    }
}

$pyVersion = try { (& python --version 2>$null).Split()[1] } catch { 'unknown' }
Write-EnvLog ("python {0} ({1} via {2})" -f $pyVersion, $variant, $envSource)
if ($variant -eq 'free-threaded' -and ($envSource -notlike 'pyenv-virtualenv*')) {
    Write-EnvLog 'note: fallback venv may not include the free-threaded build'
}

