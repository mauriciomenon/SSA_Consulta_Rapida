# Setup inicial do ambiente Python para SSA_Consulta_Rapida (Windows)
# Garante que pyenv está instalado e configura o ambiente

param(
    [string]$Variant = "stable",  # stable ou free-threaded
    [switch]$SkipPyenv,
    [switch]$Force,
    [switch]$AllowRemotePyenvInstall,
    [string]$PyenvInstallerSha256 = $env:SSA_PYENV_INSTALLER_SHA256
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
. (Join-Path $PSScriptRoot 'native_host_guard.ps1')
Assert-SsaWindowsHost -RepoRoot $repoRoot -ExpectedRoot (Get-SsaWindowsRepoRoot)
Assert-SsaWindowsVenv -VenvDir (Join-Path $repoRoot '.venv')
Assert-SsaWindowsVenv -VenvDir (Join-Path $repoRoot '.venv_ft')

function Write-EnvLog {
    param([string]$Message)
    Write-Host "[setup] $Message" -ForegroundColor Cyan
}

function Test-PyenvInstalled {
    try {
        $null = Get-Command pyenv -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

function Install-Pyenv {
    Write-EnvLog "pyenv não encontrado. Instalando pyenv-win..."
    $allowRemoteInstall = $AllowRemotePyenvInstall -or ($env:SSA_ALLOW_REMOTE_PYENV_INSTALL -eq "1")

    if (Test-Path "$env:USERPROFILE\.pyenv") {
        if ($Force) {
            if ($env:SSA_CONFIRM_REMOVE_PYENV -ne "1") {
                Write-EnvLog "Force requires SSA_CONFIRM_REMOVE_PYENV=1 before removing $env:USERPROFILE\.pyenv"
                return $false
            }
            Write-EnvLog "Removendo instalação existente..."
            Remove-Item -Recurse -Force "$env:USERPROFILE\.pyenv"
        } else {
            Write-EnvLog "pyenv já existe em $env:USERPROFILE\.pyenv mas não está no PATH"
            Write-EnvLog "Execute com -Force para reinstalar ou adicione ao PATH manualmente"
            return $false
        }
    }

    if (-not $allowRemoteInstall) {
        Write-EnvLog "Remote pyenv-win install disabled."
        Write-EnvLog "Install pyenv-win manually or pass -AllowRemotePyenvInstall with -PyenvInstallerSha256."
        return $false
    }
    if ([string]::IsNullOrWhiteSpace($PyenvInstallerSha256)) {
        Write-EnvLog "PyenvInstallerSha256 is required for remote pyenv-win install."
        return $false
    }

    $installerPath = Join-Path $env:TEMP "install-pyenv-win.ps1"
    try {
        Invoke-WebRequest -UseBasicParsing -Uri "https://raw.githubusercontent.com/pyenv-win/pyenv-win/master/pyenv-win/install-pyenv-win.ps1" -OutFile $installerPath
        $expectedHash = $PyenvInstallerSha256.Trim().ToLowerInvariant()
        $actualHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $installerPath).Hash.ToLowerInvariant()
        if ($actualHash -ne $expectedHash) {
            Write-EnvLog "pyenv-win installer SHA256 mismatch. Expected=$expectedHash Actual=$actualHash"
            return $false
        }
        & $installerPath

        # Adicionar ao PATH da sessão atual
        $env:PYENV = "$env:USERPROFILE\.pyenv\pyenv-win"
        $env:PYENV_ROOT = "$env:USERPROFILE\.pyenv\pyenv-win"
        $env:PYENV_HOME = "$env:USERPROFILE\.pyenv\pyenv-win"
        $env:PATH = "$env:PYENV\bin;$env:PYENV\shims;$env:PATH"

        Write-EnvLog "pyenv-win instalado! Reinicie o terminal ou recarregue o perfil."
        return $true
    } catch {
        Write-EnvLog "Erro ao instalar pyenv-win: $_"
        return $false
    } finally {
        Remove-Item -LiteralPath $installerPath -Force -ErrorAction SilentlyContinue
    }
}

# Main
Write-EnvLog "Verificando ambiente Python..."

if (-not $SkipPyenv) {
    if (-not (Test-PyenvInstalled)) {
        if (-not (Install-Pyenv)) {
            Write-EnvLog "Falha ao instalar pyenv. Continue manualmente ou use -SkipPyenv"
            exit 1
        }
    } else {
        Write-EnvLog "pyenv encontrado: $(pyenv --version)"
    }
}

# Determinar versão
$pythonVersionFile = Join-Path $repoRoot ".python-version"

if (Test-Path $pythonVersionFile) {
    $pythonVersion = (Get-Content $pythonVersionFile).Trim()
    Write-EnvLog "Versão Python no .python-version: $pythonVersion"
} else {
    $pythonVersion = if ($env:SSA_PYTHON_STABLE_VERSION) { $env:SSA_PYTHON_STABLE_VERSION } else { "3.13.12" }
    Write-EnvLog ".python-version ausente; criando com $pythonVersion"
    Write-EnvLog "Override: set SSA_PYTHON_STABLE_VERSION before running this setup."
    Set-Content -Path $pythonVersionFile -Value $pythonVersion
}

if ($Variant -eq "free-threaded") {
    $pythonVersion = if ($env:SSA_PYTHON_FT_VERSION) { $env:SSA_PYTHON_FT_VERSION } else { "3.14-dev" }
    Write-EnvLog "Variante free-threaded: usando $pythonVersion"
}

# Instalar Python via pyenv se necessário
if (-not $SkipPyenv -and (Test-PyenvInstalled)) {
    $installedVersions = pyenv versions --bare 2>$null
    if ($installedVersions -notcontains $pythonVersion) {
        Write-EnvLog "Instalando Python $pythonVersion via pyenv..."
        pyenv install $pythonVersion
        if ($LASTEXITCODE -ne 0) {
            Write-EnvLog "Erro ao instalar Python $pythonVersion"
            exit 1
        }
    } else {
        Write-EnvLog "Python $pythonVersion já instalado"
    }

    # Configurar versão local
    Set-Location $repoRoot
    pyenv local $pythonVersion
    Write-EnvLog "Configurado pyenv local para $pythonVersion"
}

# Verificar Python ativo
try {
    $activePython = & python --version 2>&1
    Write-EnvLog "Python ativo: $activePython"
} catch {
    Write-EnvLog "Nenhum Python encontrado! Instale manualmente ou use pyenv."
    exit 1
}

# Instalar dependências
Write-EnvLog "`nInstalar dependências agora? (y/N)"
$install = Read-Host
if ($install -eq "y" -or $install -eq "Y") {
    $reqFile = Join-Path $repoRoot "requirements_dev.txt"
    if (Test-Path $reqFile) {
        Write-EnvLog "Instalando dependências de desenvolvimento..."
        pip install -r $reqFile
    } else {
        Write-EnvLog "requirements_dev.txt não encontrado"
    }
}

Write-EnvLog "`nSetup concluído!"
Write-EnvLog "Para ativar o ambiente:"
Write-EnvLog "  - Com direnv: direnv allow"
Write-EnvLog "  - Manual: . scripts\env\direnv_common.ps1; ssa_env_apply manual"
