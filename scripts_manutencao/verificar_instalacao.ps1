# Script de Verificação Automática - SSA Consulta Rápida v3.0.7
# verificar_instalacao.ps1
# Execute com: .\verificar_instalacao.ps1

Write-Host " VERIFICAÇÃO AUTOMÁTICA DA INSTALAÇÃO" -ForegroundColor Cyan
Write-Host "=" * 50 -ForegroundColor Cyan

# Função para verificar e exibir resultado
function Test-Component {
    param(
        [string]$Name,
        [scriptblock]$Test,
        [string]$SuccessMessage,
        [string]$FailureMessage
    )
    
    Write-Host " Testando: $Name..." -NoNewline
    try {
        $result = & $Test
        if ($result) {
            Write-Host "  OK" -ForegroundColor Green
            if ($SuccessMessage) { Write-Host "   $SuccessMessage" -ForegroundColor Gray }
        } else {
            Write-Host "  FALHA" -ForegroundColor Red
            if ($FailureMessage) { Write-Host "   $FailureMessage" -ForegroundColor Yellow }
        }
        return $result
    } catch {
        Write-Host "  ERRO" -ForegroundColor Red
        Write-Host "   $($_.Exception.Message)" -ForegroundColor Yellow
        return $false
    }
}

Write-Host "`n VERIFICANDO PRÉ-REQUISITOS..." -ForegroundColor Yellow

# 1. Verificar Python
$pythonOk = Test-Component -Name "Python 3.13+" -Test {
    $version = python --version 2>$null
    if ($version -match "Python (\d+)\.(\d+)") {
        $major = [int]$Matches[1]
        $minor = [int]$Matches[2]
        return ($major -eq 3 -and $minor -ge 13) -or ($major -gt 3)
    }
    return $false
} -SuccessMessage "$(python --version)" -FailureMessage "Python 3.13+ necessário"

# 2. Verificar Git
$gitOk = Test-Component -Name "Git" -Test {
    $null = git --version 2>$null
    return $LASTEXITCODE -eq 0
} -SuccessMessage "$(git --version)" -FailureMessage "Git não encontrado"

# 3. Verificar estrutura do projeto
$structureOk = Test-Component -Name "Estrutura do Projeto" -Test {
    return (Test-Path "main.py") -and (Test-Path "requirements.txt") -and (Test-Path "core") -and (Test-Path "config")
} -SuccessMessage "Todos os arquivos principais encontrados" -FailureMessage "Arquivos principais não encontrados"

Write-Host "`n VERIFICANDO AMBIENTE PYTHON..." -ForegroundColor Yellow

# 4. Verificar ambiente virtual
$venvOk = Test-Component -Name "Ambiente Virtual" -Test {
    return Test-Path "venv" -and (Test-Path "venv\Scripts\python.exe")
} -SuccessMessage "Ambiente virtual encontrado" -FailureMessage "Execute: python -m venv venv"

# 5. Verificar se ambiente está ativo
$venvActiveOk = Test-Component -Name "Ambiente Ativo" -Test {
    $pythonPath = python -c "import sys; print(sys.executable)" 2>$null
    return $pythonPath -like "*venv*"
} -SuccessMessage "Ambiente virtual ativo" -FailureMessage "Execute: .\venv\Scripts\Activate.ps1"

Write-Host "`n VERIFICANDO DEPENDÊNCIAS..." -ForegroundColor Yellow

# 6. Verificar dependências principais
$dependenciesOk = Test-Component -Name "Dependências Python" -Test {
    $packages = @("pandas", "PyQt6", "openpyxl")
    foreach ($package in $packages) {
        $result = pip show $package 2>$null
        if (-not $result) { return $false }
    }
    return $true
} -SuccessMessage "Todas as dependências instaladas" -FailureMessage "Execute: pip install -r requirements.txt"

Write-Host "`n VERIFICANDO SISTEMA..." -ForegroundColor Yellow

# 7. Verificar importação dos módulos
$modulesOk = Test-Component -Name "Módulos do Sistema" -Test {
    $testScript = @"
import sys
sys.path.insert(0, '.')
try:
    from core import app_logic
    from armazenamento import database
    from interface import cli
    print('OK')
except ImportError as e:
    print(f'ERRO: {e}')
    exit(1)
"@
    $result = python -c $testScript 2>$null
    return $result -eq "OK"
} -SuccessMessage "Todos os módulos carregam corretamente" -FailureMessage "Problema na estrutura de módulos"

# 8. Verificar configurações
$configOk = Test-Component -Name "Arquivos de Configuração" -Test {
    return (Test-Path "config\schema.sql") -and (Test-Path "config\gui_main_preferences.json")
} -SuccessMessage "Configurações encontradas" -FailureMessage "Arquivos de configuração ausentes"

Write-Host "`n VERIFICANDO BANCO DE DADOS..." -ForegroundColor Yellow

# 9. Verificar pasta data
$dataOk = Test-Component -Name "Pasta de Dados" -Test {
    if (-not (Test-Path "data")) {
        New-Item -ItemType Directory -Path "data" -Force | Out-Null
    }
    return Test-Path "data"
} -SuccessMessage "Pasta data existe" -FailureMessage "Não foi possível criar pasta data"

# 10. Verificar criação do banco
$dbOk = Test-Component -Name "Criação do Banco" -Test {
    if (-not (Test-Path "data\ssas.db")) {
        Write-Host "`n    Criando banco de dados..." -ForegroundColor Cyan
        python main.py --reset-db 2>$null
        return $LASTEXITCODE -eq 0 -and (Test-Path "data\ssas.db")
    }
    return $true
} -SuccessMessage "Banco de dados disponível" -FailureMessage "Erro ao criar banco"

Write-Host "`n TESTANDO FUNCIONALIDADES..." -ForegroundColor Yellow

# 11. Verificar help do sistema
$helpOk = Test-Component -Name "Sistema de Help" -Test {
    $help = python main.py --help 2>$null
    return $help -like "*Consulta Rápida de SSAs*"
} -SuccessMessage "Help funcionando corretamente" -FailureMessage "Problema no sistema de help"

# 12. Verificar GUI (se possível)
$guiOk = Test-Component -Name "Interface Gráfica (PyQt6)" -Test {
    $testScript = @"
try:
    from PyQt6.QtWidgets import QApplication
    print('OK')
except ImportError as e:
    print('ERRO')
    exit(1)
"@
    $result = python -c $testScript 2>$null
    return $result -eq "OK"
} -SuccessMessage "PyQt6 funcionando" -FailureMessage "Execute: pip install --upgrade PyQt6"

Write-Host "`n RESUMO DA VERIFICAÇÃO" -ForegroundColor Magenta
Write-Host "=" * 50 -ForegroundColor Magenta

$totalTests = 12
$passedTests = 0

$results = @(
    @{Name="Python 3.13+"; Status=$pythonOk},
    @{Name="Git"; Status=$gitOk},
    @{Name="Estrutura do Projeto"; Status=$structureOk},
    @{Name="Ambiente Virtual"; Status=$venvOk},
    @{Name="Ambiente Ativo"; Status=$venvActiveOk},
    @{Name="Dependências Python"; Status=$dependenciesOk},
    @{Name="Módulos do Sistema"; Status=$modulesOk},
    @{Name="Arquivos de Configuração"; Status=$configOk},
    @{Name="Pasta de Dados"; Status=$dataOk},
    @{Name="Banco de Dados"; Status=$dbOk},
    @{Name="Sistema de Help"; Status=$helpOk},
    @{Name="Interface Gráfica"; Status=$guiOk}
)

foreach ($result in $results) {
    $status = if ($result.Status) { " OK" } else { " FALHA" }
    $color = if ($result.Status) { "Green" } else { "Red" }
    Write-Host "  $($result.Name): " -NoNewline
    Write-Host $status -ForegroundColor $color
    if ($result.Status) { $passedTests++ }
}

Write-Host "`n RESULTADO FINAL:" -ForegroundColor Cyan
$percentage = [math]::Round(($passedTests / $totalTests) * 100)
Write-Host "  $passedTests/$totalTests testes aprovados ($percentage%)" -ForegroundColor $(if ($percentage -ge 90) { "Green" } elseif ($percentage -ge 70) { "Yellow" } else { "Red" })

if ($percentage -ge 90) {
    Write-Host "`n INSTALAÇÃO PERFEITA!" -ForegroundColor Green
    Write-Host "  Sistema pronto para uso. Execute:" -ForegroundColor Gray
    Write-Host "  python main.py" -ForegroundColor White
} elseif ($percentage -ge 70) {
    Write-Host "`n  INSTALAÇÃO FUNCIONAL" -ForegroundColor Yellow
    Write-Host "  Sistema pode funcionar, mas há problemas menores." -ForegroundColor Gray
    Write-Host "  Consulte o GUIA_MIGRACAO_NOVA_INSTALACAO.md" -ForegroundColor White
} else {
    Write-Host "`n INSTALAÇÃO COM PROBLEMAS" -ForegroundColor Red
    Write-Host "  Revise os erros e consulte o guia de migração." -ForegroundColor Gray
    Write-Host "  GUIA_MIGRACAO_NOVA_INSTALACAO.md" -ForegroundColor White
}

Write-Host "`n PRÓXIMOS PASSOS:" -ForegroundColor Cyan
if ($percentage -ge 70) {
    Write-Host "  1. python main.py --help           # Ver todas as opções" -ForegroundColor White
    Write-Host "  2. python main.py                  # Iniciar CLI" -ForegroundColor White
    Write-Host "  3. python main.py --gui            # Iniciar GUI" -ForegroundColor White
    Write-Host "  4. python main.py --optimized      # Modo otimizado" -ForegroundColor White
} else {
    Write-Host "  1. Revisar erros acima" -ForegroundColor White
    Write-Host "  2. Consultar GUIA_MIGRACAO_NOVA_INSTALACAO.md" -ForegroundColor White
    Write-Host "  3. Executar novamente este script" -ForegroundColor White
}

Write-Host "`n" -ForegroundColor Gray
