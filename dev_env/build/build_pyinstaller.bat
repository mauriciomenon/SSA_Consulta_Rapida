@echo off
setlocal EnableExtensions EnableDelayedExpansion
REM Build script PyInstaller (windows_amd64) com uv/python 3.13.

set "SILENT=0"
set "WITH_LOCAL_DATA=0"
if not "%~1"=="" (
    for %%A in (%*) do (
        if /I "%%~A"=="--silent" set "SILENT=1"
        if /I "%%~A"=="--with-local-data" set "WITH_LOCAL_DATA=1"
    )
)

for %%I in ("%~dp0..\..") do set "REPO_ROOT=%%~fI"
set "LOG_DIR=%REPO_ROOT%\launchers\logs"
set "LOG_FILE=%LOG_DIR%\build_pyinstaller_windows_amd64.log"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

set "UV_PYTHON=3.13"
set "UV_MANAGED_PYTHON=true"
set "UV_PROJECT_ENVIRONMENT=.venv-win"

if "%SILENT%"=="1" (
    uv run --python 3.13 "%REPO_ROOT%\launchers\build_multiplatform.py" --platform windows_amd64 --clean >nul 2>&1
) else (
    echo Limpando artefatos PyInstaller anteriores...
    uv run --python 3.13 "%REPO_ROOT%\launchers\build_multiplatform.py" --platform windows_amd64 --clean
)

if errorlevel 1 (
    echo Limpeza PyInstaller falhou.
    if "%SILENT%"=="0" pause
    exit /b 1
)

if "%SILENT%"=="1" (
    echo [build_pyinstaller] modo silencioso ativo. log: "%LOG_FILE%"
    uv run --python 3.13 "%REPO_ROOT%\launchers\build_multiplatform.py" --platform windows_amd64 --apps cli gui > "%LOG_FILE%" 2>&1
) else (
    echo Iniciando build PyInstaller windows_amd64...
    uv run --python 3.13 "%REPO_ROOT%\launchers\build_multiplatform.py" --platform windows_amd64 --apps cli gui
)

if errorlevel 1 (
    echo Build PyInstaller falhou. Veja o log: "%LOG_FILE%"
    if "%SILENT%"=="0" pause
    exit /b 1
)

if "%SILENT%"=="1" (
    uv run --python 3.13 "%REPO_ROOT%\scripts\sync_pyinstaller_outputs.py" --platform windows_amd64 --quiet >> "%LOG_FILE%" 2>&1
) else (
    uv run --python 3.13 "%REPO_ROOT%\scripts\sync_pyinstaller_outputs.py" --platform windows_amd64
)

if errorlevel 1 (
    echo Build PyInstaller concluiu, mas sincronizacao de saida equivalente falhou. Veja o log: "%LOG_FILE%"
    if "%SILENT%"=="0" pause
    exit /b 1
)

if "%WITH_LOCAL_DATA%"=="1" (
    if "%SILENT%"=="1" (
        uv run --python 3.13 "%REPO_ROOT%\scripts\copy_data_to_builds.py" --build-system pyinstaller --allow-local-data >> "%LOG_FILE%" 2>&1
    ) else (
        uv run --python 3.13 "%REPO_ROOT%\scripts\copy_data_to_builds.py" --build-system pyinstaller --allow-local-data
    )

    if errorlevel 1 (
        echo Build PyInstaller concluiu, mas copia de dados falhou. Veja o log: "%LOG_FILE%"
        if "%SILENT%"=="0" pause
        exit /b 1
    )
) else (
    if "%SILENT%"=="1" (
        echo [build_pyinstaller] pulando copia de dados locais. Use --with-local-data para habilitar. >> "%LOG_FILE%"
    ) else (
        echo INFO Pulando copia de dados locais. Use --with-local-data para habilitar.
    )
)

echo Build PyInstaller concluido com sucesso.
echo Artefatos em: "%REPO_ROOT%\launchers\dist\windows_amd64" e "%REPO_ROOT%\builds\pyinstaller\windows_amd64"
if "%SILENT%"=="0" (
    set /p "DO_CLEANUP=Executar cleanup TEMP agora? [s/N]: "
    if /I "!DO_CLEANUP!"=="s" (
        uv run --python 3.13 "%REPO_ROOT%\scripts\cleanup_build_artifacts.py" --scope temp
    )
)
if "%SILENT%"=="0" pause
exit /b 0
