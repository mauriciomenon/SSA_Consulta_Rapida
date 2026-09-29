# Script de teste/validação do ambiente Python
# Verifica se o setup está funcionando corretamente

param(
    [switch]$Verbose
)

$ErrorActionPreference = "Continue"
$testsPassed = 0
$testsFailed = 0

function Write-TestLog {
    param(
        [string]$Message,
        [string]$Type = "INFO"
    )
    $color = switch ($Type) {
        "PASS" { "Green" }
        "FAIL" { "Red" }
        "WARN" { "Yellow" }
        default { "Cyan" }
    }
    Write-Host "[$Type] $Message" -ForegroundColor $color
}

function Test-Condition {
    param(
        [string]$Name,
        [scriptblock]$Condition,
        [string]$FailMessage = "Test failed"
    )
    try {
        if (& $Condition) {
            Write-TestLog "$Name" "PASS"
            $script:testsPassed++
            return $true
        } else {
            Write-TestLog "$Name - $FailMessage" "FAIL"
            $script:testsFailed++
            return $false
        }
    } catch {
        Write-TestLog "$Name - Exception: $_" "FAIL"
        $script:testsFailed++
        return $false
    }
}

Write-TestLog "Iniciando validação do ambiente SSA_Consulta_Rapida..." "INFO"
Write-TestLog ""

# Test 1: Arquivos de bootstrap existem
Test-Condition "direnv_common.ps1 existe" {
    Test-Path "$PSScriptRoot\direnv_common.ps1"
}

Test-Condition "direnv_common.sh existe" {
    Test-Path "$PSScriptRoot\direnv_common.sh"
}

Test-Condition ".envrc existe na raiz" {
    Test-Path "$PSScriptRoot\..\..\.envrc"
}

# Test 2: .python-version tem conteúdo válido
Test-Condition ".python-version tem formato válido" {
    $pythonVersionFile = "$PSScriptRoot\..\..\.python-version"
    if (Test-Path $pythonVersionFile) {
        $version = (Get-Content $pythonVersionFile).Trim()
        $version -match '^\d+\.\d+(\.\d+)?$'
    } else {
        $false
    }
}

# Test 3: Scripts de setup existem e são executáveis
Test-Condition "setup_env.ps1 existe" {
    Test-Path "$PSScriptRoot\setup_env.ps1"
}

Test-Condition "setup_env.sh existe" {
    Test-Path "$PSScriptRoot\setup_env.sh"
}

# Test 4: Tentar carregar direnv_common.ps1 sem erros
Write-TestLog ""
Write-TestLog "Testando carregamento de direnv_common.ps1..." "INFO"

try {
    # Limpar ambiente primeiro
    Remove-Item Env:SSA_* -ErrorAction SilentlyContinue
    Remove-Item Env:PYENV_VERSION -ErrorAction SilentlyContinue

    # Source o script
    . "$PSScriptRoot\direnv_common.ps1"

    # Test 5: Funções foram definidas
    Test-Condition "Função ssa_env_apply definida" {
        Get-Command ssa_env_apply -ErrorAction SilentlyContinue
    }

    Test-Condition "Função ssa_env__determine_variant definida" {
        Get-Command ssa_env__determine_variant -ErrorAction SilentlyContinue
    }

    Test-Condition "Função ssa_env__init_pyenv definida" {
        Get-Command ssa_env__init_pyenv -ErrorAction SilentlyContinue
    }

    # Test 6: Variáveis de ambiente foram setadas
    Test-Condition "SSA_ENV_COMMON_SOURCED está setado" {
        $env:SSA_ENV_COMMON_SOURCED -eq "1"
    }

    # Test 7: Determinar variante funciona
    ssa_env__determine_variant

    Test-Condition "SSA_ENV_VARIANT foi definido" {
        $null -ne $env:SSA_ENV_VARIANT
    }

    Test-Condition "SSA_ENV_PY_VERSION foi definido" {
        $null -ne $env:SSA_ENV_PY_VERSION
    }

    Test-Condition "SSA_ENV_VENV_DIR foi definido" {
        $null -ne $env:SSA_ENV_VENV_DIR
    }

    if ($Verbose) {
        Write-TestLog ""
        Write-TestLog "Variáveis de ambiente detectadas:" "INFO"
        Write-TestLog "  SSA_ENV_VARIANT: $env:SSA_ENV_VARIANT"
        Write-TestLog "  SSA_ENV_PY_VERSION: $env:SSA_ENV_PY_VERSION"
        Write-TestLog "  SSA_ENV_VENV_DIR: $env:SSA_ENV_VENV_DIR"
        Write-TestLog "  SSA_ENV_PYENV_NAME: $env:SSA_ENV_PYENV_NAME"
    }

} catch {
    Write-TestLog "Erro ao carregar direnv_common.ps1: $_" "FAIL"
    $testsFailed++
}

# Test 8: pyenv disponível (warning se não estiver)
if (Get-Command pyenv -ErrorAction SilentlyContinue) {
    Write-TestLog "pyenv está disponível: $(pyenv --version)" "PASS"
    $testsPassed++

    # Test 9: Versão Python do .python-version está instalada
    $pythonVersionFile = "$PSScriptRoot\..\..\.python-version"
    if (Test-Path $pythonVersionFile) {
        $requiredVersion = (Get-Content $pythonVersionFile).Trim()
        $installedVersions = pyenv versions --bare 2>$null

        if ($installedVersions -contains $requiredVersion) {
            Write-TestLog "Python $requiredVersion está instalado via pyenv" "PASS"
            $testsPassed++
        } else {
            Write-TestLog "Python $requiredVersion NÃO está instalado (execute setup_env.ps1)" "WARN"
        }
    }
} else {
    Write-TestLog "pyenv não encontrado (ambiente usará venv local ou Python do sistema)" "WARN"
}

# Test 10: Requirements files existem
Write-TestLog ""
Write-TestLog "Verificando requirements files..." "INFO"

$reqFiles = @(
    "..\..\requirements.txt",
    "..\..\requirements_dev.txt",
    "..\..\launchers\platforms\windows_amd64\requirements.txt",
    "..\..\launchers\platforms\macos_arm64\requirements.txt",
    "..\..\launchers\platforms\debian_amd64\requirements.txt"
)

foreach ($reqFile in $reqFiles) {
    $fullPath = Join-Path $PSScriptRoot $reqFile
    if (Test-Path $fullPath) {
        Write-TestLog "$(Split-Path -Leaf $fullPath) existe" "PASS"
        $testsPassed++
    } else {
        Write-TestLog "$(Split-Path -Leaf $fullPath) NÃO encontrado" "FAIL"
        $testsFailed++
    }
}

# Summary
Write-TestLog ""
Write-TestLog "========================" "INFO"
Write-TestLog "Testes passaram: $testsPassed" "PASS"
if ($testsFailed -gt 0) {
    Write-TestLog "Testes falharam: $testsFailed" "FAIL"
    exit 1
} else {
    Write-TestLog "Todos os testes passaram!" "PASS"
    Write-TestLog ""
    Write-TestLog "Próximos passos:" "INFO"
    Write-TestLog "  1. Execute: scripts\env\setup_env.ps1" "INFO"
    Write-TestLog "  2. Ou com direnv: direnv allow" "INFO"
    exit 0
}
