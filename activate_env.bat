@echo off
REM Batch script para ativar venv automaticamente no Windows

if not exist ".venv" (
    echo Criando ambiente virtual...
    python -m venv .venv
)

echo Ativando ambiente virtual...
call .venv\Scripts\activate.bat

REM Instalar dependências se requirements.txt existir
if exist "requirements.txt" (
    echo Instalando dependências...
    pip install -r requirements.txt > nul 2>&1
)

echo Ambiente Python configurado.
echo Para desativar: deactivate
