@echo off
setlocal EnableExtensions EnableDelayedExpansion
REM Build script PyInstaller (windows_arm64) com uv/python 3.13.

set "SILENT=0"
set "WITH_RUNTIME_DB=0"
if not "%~1"=="" (
    for %%A in (%*) do (
        if /I "%%~A"=="--silent" set "SILENT=1"
        if /I "%%~A"=="--with-runtime-db" set "WITH_RUNTIME_DB=1"
        if /I "%%~A"=="--with-local-data" set "WITH_RUNTIME_DB=1"
    )
)

for %%I in ("%~dp0..\..") do set "REPO_ROOT=%%~fI"
set "LOG_DIR=%REPO_ROOT%\launchers\logs"
set "LOG_FILE=%LOG_DIR%\build_pyinstaller_windows_arm64.log"
set "RUNTIME_DB_ARGS="
if "%WITH_RUNTIME_DB%"=="1" set "RUNTIME_DB_ARGS=--runtime-db "%REPO_ROOT%\data\ssas.db""

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

set "UV_PYTHON=%SSA_WINDOWS_ARM64_PYTHON%"
if not defined UV_PYTHON set "UV_PYTHON=%LOCALAPPDATA%\Programs\Python\Python313-arm64\python.exe"
set "UV_MANAGED_PYTHON=false"
set "UV_PROJECT_ENVIRONMENT=.venv-win-arm64"

if not exist "%UV_PYTHON%" (
    echo Python ARM64 nao encontrado. Defina SSA_WINDOWS_ARM64_PYTHON com o caminho do Python nativo.
    exit /b 1
)
uv run --no-project --no-sync --python "%UV_PYTHON%" python -c "import sysconfig; raise SystemExit(0 if sysconfig.get_platform() == 'win-arm64' else 1)"
if errorlevel 1 (
    echo Python incompativel: esperado win-arm64.
    exit /b 1
)
cd /d "%REPO_ROOT%"
if errorlevel 1 exit /b 1
uv sync --frozen --python "%UV_PYTHON%" --extra build
if errorlevel 1 exit /b 1

if "%SILENT%"=="1" (
    uv run --no-sync --python "%UV_PYTHON%" "%REPO_ROOT%\launchers\build_multiplatform.py" --platform windows_arm64 --clean >nul 2>&1
) else (
    echo Limpando artefatos PyInstaller anteriores...
    uv run --no-sync --python "%UV_PYTHON%" "%REPO_ROOT%\launchers\build_multiplatform.py" --platform windows_arm64 --clean
)

if errorlevel 1 (
    echo Limpeza PyInstaller falhou.
    if "%SILENT%"=="0" pause
    exit /b 1
)

if "%SILENT%"=="1" (
    echo [build_pyinstaller] modo silencioso ativo. log: "%LOG_FILE%"
    uv run --no-sync --python "%UV_PYTHON%" "%REPO_ROOT%\launchers\build_multiplatform.py" --platform windows_arm64 --apps cli gui %RUNTIME_DB_ARGS% > "%LOG_FILE%" 2>&1
) else (
    echo Iniciando build PyInstaller windows_arm64...
    uv run --no-sync --python "%UV_PYTHON%" "%REPO_ROOT%\launchers\build_multiplatform.py" --platform windows_arm64 --apps cli gui %RUNTIME_DB_ARGS%
)

if errorlevel 1 (
    echo Build PyInstaller falhou. Veja o log: "%LOG_FILE%"
    if "%SILENT%"=="0" pause
    exit /b 1
)

if "%SILENT%"=="1" (
    uv run --no-sync --python "%UV_PYTHON%" "%REPO_ROOT%\scripts\sync_pyinstaller_outputs.py" --platform windows_arm64 --quiet >> "%LOG_FILE%" 2>&1
) else (
    uv run --no-sync --python "%UV_PYTHON%" "%REPO_ROOT%\scripts\sync_pyinstaller_outputs.py" --platform windows_arm64
)

if errorlevel 1 (
    echo Build PyInstaller concluiu, mas sincronizacao de saida equivalente falhou. Veja o log: "%LOG_FILE%"
    if "%SILENT%"=="0" pause
    exit /b 1
)

if "%WITH_RUNTIME_DB%"=="0" (
    if "%SILENT%"=="1" (
        echo [build_pyinstaller] banco operacional nao solicitado. Use --with-runtime-db para incluir data\ssas.db. >> "%LOG_FILE%"
    ) else (
        echo INFO Banco operacional nao solicitado. Use --with-runtime-db para incluir data\ssas.db.
    )
)

echo Build PyInstaller concluido com sucesso.
echo Artefatos em: "%REPO_ROOT%\launchers\dist\windows_arm64" e "%REPO_ROOT%\builds\pyinstaller\windows_arm64"
if "%SILENT%"=="0" (
    set /p "DO_CLEANUP=Executar cleanup TEMP agora? [s/N]: "
    if /I "!DO_CLEANUP!"=="s" (
        uv run --no-sync --python "%UV_PYTHON%" "%REPO_ROOT%\scripts\cleanup_build_artifacts.py" --scope temp
    )
)
if "%SILENT%"=="0" pause
exit /b 0
