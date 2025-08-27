# PowerShell script para ativar venv automaticamente

if (-not (Test-Path ".venv")) {
    Write-Host "Criando ambiente virtual..." -ForegroundColor Yellow
    python -m venv .venv
}

Write-Host "Ativando ambiente virtual..." -ForegroundColor Green
& ".venv\Scripts\Activate.ps1"

# Instalar dependências se requirements.txt existir
if (Test-Path "requirements.txt") {
    Write-Host "Instalando dependências..." -ForegroundColor Blue
    pip install -r requirements.txt | Out-Null
}

Write-Host "Ambiente Python configurado." -ForegroundColor Green
Write-Host "Para desativar: deactivate" -ForegroundColor Cyan
