[CmdletBinding()]
param(
    [string]$Variant
)

function Write-EnvLog {
    param([string]$Message)
    Write-Host "[env] $Message"
}

function ConvertTo-EnvNameSegment {
    param([string]$Value)
    if (-not $Value) { return 'python' }
    $result = $Value.ToLowerInvariant()
    $result = $result -replace '[^a-z0-9]+', '_'
    $result = $result.Trim('_')
    if (-not $result) { $result = 'python' }
    return $result
}

$repoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
if (-not $repoRoot) {
    $repoRoot = (Get-Location).Path
}
$guardScript = Join-Path $repoRoot 'scripts\env\native_host_guard.ps1'
. $guardScript
Assert-SsaWindowsHost -RepoRoot $repoRoot -ExpectedRoot (Get-SsaWindowsRepoRoot)
Assert-SsaWindowsVenv -VenvDir (Join-Path $repoRoot '.venv')
Assert-SsaWindowsVenv -VenvDir (Join-Path $repoRoot '.venv_ft')

$requestedVariant = if ($Variant) {
    $Variant
} elseif ($env:SSA_USE_FREE_THREADED -and $env:SSA_USE_FREE_THREADED -ne '0') {
    'free-threaded'
} elseif ($env:SSA_PYTHON_VARIANT) {
    $env:SSA_PYTHON_VARIANT
} else {
    'stable'
}

$stableVersion = if ($env:SSA_PYTHON_STABLE_VERSION) { $env:SSA_PYTHON_STABLE_VERSION } else { '3.13.12' }
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

$pyenvEnvName = "ssa_consulta_{0}_{1}" -f ($variant -replace '-', '_'), (ConvertTo-EnvNameSegment -Value $targetVersion)
$envSource = $null

$pyenv = Get-Command pyenv -ErrorAction SilentlyContinue
$pyenvAvailable = $false
$pyenvHasVirtualenv = $false
if ($pyenv) {
    $pyenvAvailable = $true
    try {
        $commands = pyenv commands
        if ($LASTEXITCODE -ne 0) {
            throw "pyenv commands failed with exit code $LASTEXITCODE"
        }
        if ($commands -match '(?m)^virtualenv$') {
            $pyenvHasVirtualenv = $true
        }
    } catch {
        Write-EnvLog "warn: pyenv inspection failed; using local venv fallback ($_)"
        $pyenvAvailable = $false
    }
}

if ($pyenvAvailable) {
    try {
        $versions = (pyenv versions --bare) 2>$null
        if ($LASTEXITCODE -ne 0) {
            throw "pyenv versions failed with exit code $LASTEXITCODE"
        }
        $versionList = @()
        if ($versions) { $versionList = $versions -split "`n" }
        if (-not ($versionList -contains $targetVersion)) {
            Write-EnvLog "pyenv: installing Python $targetVersion (first run may take a while)"
            pyenv install $targetVersion | Out-Null
            if ($LASTEXITCODE -ne 0) {
                throw "pyenv install failed with exit code $LASTEXITCODE"
            }
        }
        if ($pyenvHasVirtualenv) {
            $venvs = (pyenv virtualenvs --bare) 2>$null
            if ($LASTEXITCODE -ne 0) {
                throw "pyenv virtualenvs failed with exit code $LASTEXITCODE"
            }
            $venvList = @()
            if ($venvs) { $venvList = $venvs -split "`n" }
            if (-not ($venvList -contains $pyenvEnvName)) {
                Write-EnvLog "pyenv: creating virtualenv $pyenvEnvName"
                $previousVersion = $env:PYENV_VERSION
                try {
                    $env:PYENV_VERSION = $targetVersion
                    $backend = pyenv virtualenv --version
                    if ($LASTEXITCODE -ne 0) { throw 'Falha ao identificar backend do pyenv virtualenv' }
                } finally {
                    $env:PYENV_VERSION = $previousVersion
                }
                $pipOption = if ($backend -match '\(virtualenv ') { '--no-pip' } else { '--without-pip' }
                pyenv virtualenv $pipOption $targetVersion $pyenvEnvName | Out-Null
                if ($LASTEXITCODE -ne 0) {
                    throw "pyenv virtualenv failed with exit code $LASTEXITCODE"
                }
            }
            pyenv activate $pyenvEnvName | Out-Null
            if ($LASTEXITCODE -ne 0) {
                throw "pyenv activate failed with exit code $LASTEXITCODE"
            }
            $envSource = "pyenv-virtualenv:$pyenvEnvName"
        } else {
            pyenv shell $targetVersion | Out-Null
            if ($LASTEXITCODE -ne 0) {
                throw "pyenv shell failed with exit code $LASTEXITCODE"
            }
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
    $numericVersion = if ($targetVersion -match '^(\d+\.\d+(?:\.\d+)?)(?:t|\+freethreaded)?(?:-dev)?$') { $Matches[1] } else { $null }
    if (-not (Test-Path $activatePath)) {
        if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
            throw 'uv nao encontrado no PATH para criar o ambiente.'
        }
        $uvPythonVersion = if ($variant -eq 'free-threaded' -and $numericVersion) {
            "$numericVersion+freethreaded"
        } else { $targetVersion }
        Write-EnvLog "Criando $venvDir com Python $uvPythonVersion via uv"
        uv venv --python $uvPythonVersion $venvPath
        if ($LASTEXITCODE -ne 0) {
            throw "Falha ao criar $venvPath com Python $uvPythonVersion"
        }
    }
    $venvPython = Join-Path $venvPath 'Scripts/python.exe'
    if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
        throw "Executavel Python ausente em $venvPath"
    }
    if ($numericVersion) {
        $actualVersion = & $venvPython -c 'import platform; print(platform.python_version())'
        if ($LASTEXITCODE -ne 0 -or $actualVersion -notmatch ('^' + [regex]::Escape($numericVersion) + '(\.|$)')) {
            throw "Versao Python invalida em $venvPath; esperado $targetVersion"
        }
    }
    $envSource = "venv:$venvDir"
}

if ($variant -eq 'free-threaded') {
    $selectedPython = if ($envSource -like 'venv:*') { $venvPython } else { 'python' }
    & $selectedPython -c 'import sys, sysconfig; sys.exit(0 if sysconfig.get_config_var("Py_GIL_DISABLED") else 1)'
    if ($LASTEXITCODE -ne 0) {
        throw 'O Python selecionado nao e uma build free-threaded.'
    }
}

if ($envSource -like 'venv:*') {
    . $activatePath
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

