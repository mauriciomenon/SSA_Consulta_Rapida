# activate_env.ps1 - Script de Ativação do Ambiente SSA Consulta Rápida v3.10

Write-Host "🚀 SSA Consulta Rápida v3.10 - Ativação do Ambiente" -ForegroundColor Cyan

# Verificar se estamos no diretório correto
if (-not (Test-Path "main.py")) {
    Write-Host "❌ Execute este script na pasta raiz do projeto SSA_Consulta_Rapida" -ForegroundColor Red
    exit 1
}

# Verificar/criar ambiente virtual
$venvPath = if (Test-Path "venv") { "venv" } else { ".venv" }

if (-not (Test-Path $venvPath)) {
    Write-Host "📦 Criando ambiente virtual em '$venvPath'..." -ForegroundColor Yellow
    python -m venv $venvPath
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Erro ao criar ambiente virtual" -ForegroundColor Red
        exit 1
    }
}

# Ativar ambiente
Write-Host "🔄 Ativando ambiente virtual..." -ForegroundColor Green
$activateScript = Join-Path $venvPath "Scripts\Activate.ps1"

if (Test-Path $activateScript) {
    & $activateScript
} else {
    Write-Host "❌ Script de ativação não encontrado: $activateScript" -ForegroundColor Red
    exit 1
}

# Verificar se está ativo
$pythonPath = python -c "import sys; print(sys.executable)" 2>$null
if ($pythonPath -like "*$venvPath*") {
    Write-Host "✅ Ambiente virtual ativo" -ForegroundColor Green
} else {
    Write-Host "⚠️  Ambiente pode não estar ativo corretamente" -ForegroundColor Yellow
}

# Instalar/atualizar dependências
if (Test-Path "requirements.txt") {
    Write-Host "📚 Verificando dependências..." -ForegroundColor Blue
    
    # Verificar se as principais dependências estão instaladas
    $mainPackages = @("pandas", "PyQt6", "openpyxl")
    $needsInstall = $false
    
    foreach ($package in $mainPackages) {
        $installed = pip show $package 2>$null
        if (-not $installed) {
            $needsInstall = $true
            break
        }
    }
    
    if ($needsInstall) {
        Write-Host "🔧 Instalando dependências..." -ForegroundColor Yellow
        pip install -r requirements.txt
        if ($LASTEXITCODE -ne 0) {
            Write-Host "❌ Erro ao instalar dependências" -ForegroundColor Red
        } else {
            Write-Host "✅ Dependências instaladas" -ForegroundColor Green
        }
    } else {
        Write-Host "✅ Dependências já instaladas" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "🎯 AMBIENTE CONFIGURADO!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Comandos disponíveis:" -ForegroundColor Cyan
Write-Host "  python main.py --help     # Ver todas as opções" -ForegroundColor White
Write-Host "  python main.py            # Iniciar CLI" -ForegroundColor White
Write-Host "  python main.py --gui      # Iniciar GUI" -ForegroundColor White
Write-Host "  .\verificar_instalacao.ps1 # Verificar sistema" -ForegroundColor White
Write-Host ""
Write-Host "💡 Para desativar o ambiente: deactivate" -ForegroundColor Gray
