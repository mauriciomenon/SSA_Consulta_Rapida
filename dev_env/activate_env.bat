@echo off
REM Batch script para ativar venv automaticamente no Windows (UTF-8)

REM Forcar UTF-8 no console atual

REM Garantir UTF-8 no Python (stdout/stderr/leitura de arquivos padrão)

REM Escolher venv existente: .venv_build > .venv
set "VENV_DIR=.venv"
if exist ".venv_build" set "VENV_DIR=.venv_build"
if not exist "%VENV_DIR%" (
    echo Criando ambiente virtual em %VENV_DIR%...
    python -m venv %VENV_DIR%
)

echo Ativando ambiente virtual %VENV_DIR%...
call "%VENV_DIR%\Scripts\activate.bat"

REM Instalar dependencias se requirements.txt existir
if exist "requirements.txt" (
    echo Instalando dependencias...
    pip install -r requirements.txt > nul 2>&1
)

echo Ambiente Python configurado (UTF-8 ativo).
echo Para desativar: deactivate

