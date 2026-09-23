@echo off
REM Batch script para ativar venv automaticamente no Windows (UTF-8)

REM Forcar UTF-8 no console atual

REM Garantir UTF-8 no Python (stdout/stderr/leitura de arquivos padrão)

cd /d "%~dp0.." || exit /b 1
where uv > nul 2>&1
if errorlevel 1 (
    echo Erro: uv nao encontrado no PATH.
    exit /b 1
)

REM Escolher venv existente: .venv_build > .venv
set "VENV_DIR=.venv"
if exist ".venv_build" set "VENV_DIR=.venv_build"
if not exist "%VENV_DIR%" (
    echo Criando ambiente virtual em %VENV_DIR%...
    uv venv --python python "%VENV_DIR%"
    if errorlevel 1 (
        echo Erro ao criar ambiente virtual.
        exit /b 1
    )
)

if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo Erro: ambiente virtual incompleto em %VENV_DIR%.
    exit /b 1
)
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo Erro: script de ativacao ausente em %VENV_DIR%.
    exit /b 1
)

echo Ativando ambiente virtual %VENV_DIR%...
call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 exit /b 1

REM Instalar dependencias fixadas no ambiente selecionado
set "UV_PROJECT_ENVIRONMENT=%CD%\%VENV_DIR%"
echo Instalando dependencias com uv...
uv sync --project "%CD%" --python "%UV_PROJECT_ENVIRONMENT%\Scripts\python.exe" --frozen --no-dev --inexact
if errorlevel 1 (
    echo Erro ao instalar dependencias com uv.
    exit /b 1
)

echo Ambiente Python configurado (UTF-8 ativo).
echo Para desativar: deactivate

