# Setup inicial do ambiente Python para SSA_Consulta_Rapida (Windows)
# Garante que pyenv está instalado e configura o ambiente

param(
    [string]$Variant = "stable",  # stable ou free-threaded
    [switch]$SkipPyenv,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

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
    
    if (Test-Path "$env:USERPROFILE\.pyenv") {
        if ($Force) {
            Write-EnvLog "Removendo instalação existente..."
            Remove-Item -Recurse -Force "$env:USERPROFILE\.pyenv"
        } else {
            Write-EnvLog "pyenv já existe em $env:USERPROFILE\.pyenv mas não está no PATH"
            Write-EnvLog "Execute com -Force para reinstalar ou adicione ao PATH manualmente"
            return $false
        }
    }
    
    try {
        Invoke-WebRequest -UseBasicParsing -Uri "https://raw.githubusercontent.com/pyenv-win/pyenv-win/master/pyenv-win/install-pyenv-win.ps1" -OutFile "$env:TEMP\install-pyenv-win.ps1"
        & "$env:TEMP\install-pyenv-win.ps1"
        
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
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$pythonVersionFile = Join-Path $repoRoot ".python-version"

if (Test-Path $pythonVersionFile) {
    $pythonVersion = (Get-Content $pythonVersionFile).Trim()
    Write-EnvLog "Versão Python no .python-version: $pythonVersion"
} else {
    $pythonVersion = "3.13.9"
    Write-EnvLog "Criando .python-version com $pythonVersion"
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
