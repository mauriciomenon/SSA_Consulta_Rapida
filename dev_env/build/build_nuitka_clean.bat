@echo off
setlocal EnableExtensions EnableDelayedExpansion
REM Build script Nuitka (windows_amd64) com uv/python 3.13.

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
set "LOG_FILE=%LOG_DIR%\build_nuitka_windows_amd64.log"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
if not exist "%REPO_ROOT%\builds\nuitka\windows_amd64" mkdir "%REPO_ROOT%\builds\nuitka\windows_amd64"

set "UV_PYTHON=3.13"
set "UV_MANAGED_PYTHON=true"
set "UV_PROJECT_ENVIRONMENT=.venv-win"
if not defined PROCESSOR_ARCHITECTURE set "PROCESSOR_ARCHITECTURE=AMD64"
if not defined PROCESSOR_ARCHITEW6432 set "PROCESSOR_ARCHITEW6432=AMD64"

for /f "tokens=1,2 delims=|" %%A in ('uv run --python 3.13 python -c "import json,pathlib; v=str(json.loads(pathlib.Path('config/version.json').read_text(encoding='utf-8')).get('version_short','')).strip(); assert v, 'version_short ausente'; f='.'.join((v.split('.')+['0','0','0'])[:4]); print(v+'|'+f)"') do (
    set "APP_VERSION=%%A"
    set "FILE_VERSION=%%B"
)
if not defined APP_VERSION (
    echo Erro ao carregar versao de config\version.json.
    exit /b 1
)
if not defined FILE_VERSION (
    echo Erro ao calcular file version de config\version.json.
    exit /b 1
)

set "BUILD_METADATA_DIR=%REPO_ROOT%\builds\metadata"
if not exist "%BUILD_METADATA_DIR%" mkdir "%BUILD_METADATA_DIR%"
set "BUILD_INFO_FILE=%BUILD_METADATA_DIR%\build_info_windows_amd64_nuitka.json"
uv run --python 3.13 "%REPO_ROOT%\dev_env\build\write_build_info.py" --repo-root "%REPO_ROOT%" --output "%BUILD_INFO_FILE%" --build-system nuitka --platform windows_amd64 --app-version "%APP_VERSION%"
if errorlevel 1 (
    echo Erro ao gerar build_info.json.
    exit /b 1
)

if exist "%REPO_ROOT%\builds\nuitka\windows_amd64\SSA_GUI_v%APP_VERSION%_windows_amd64.dist" rmdir /s /q "%REPO_ROOT%\builds\nuitka\windows_amd64\SSA_GUI_v%APP_VERSION%_windows_amd64.dist"
if exist "%REPO_ROOT%\builds\nuitka\windows_amd64\SSA_CLI_v%APP_VERSION%_windows_amd64.dist" rmdir /s /q "%REPO_ROOT%\builds\nuitka\windows_amd64\SSA_CLI_v%APP_VERSION%_windows_amd64.dist"

set "BASE_CMD=uv run --python 3.13 --extra build python -m nuitka --standalone --assume-yes-for-downloads --follow-imports --enable-plugin=pyqt6 --company-name=SSA --product-name=Consulta_Rapida_de_SSAs --file-version=%FILE_VERSION% --product-version=%FILE_VERSION% --include-data-dir=config=config --include-data-dir=resources=resources --include-data-file=docs/GUIA_MIGRACAO_NOVA_INSTALACAO.md=docs/GUIA_MIGRACAO_NOVA_INSTALACAO.md --include-data-file=%BUILD_INFO_FILE%=config/build_info.json --output-dir=builds/nuitka/windows_amd64"

if "%SILENT%"=="1" (
    echo [build_nuitka] modo silencioso ativo. log: "%LOG_FILE%"
    call %BASE_CMD% --output-filename=SSA_GUI_v%APP_VERSION%_windows_amd64.exe --windows-console-mode=disable --windows-icon-from-ico=resources/app_icon.ico launchers/gui_entry.py > "%LOG_FILE%" 2>&1
) else (
    call %BASE_CMD% --output-filename=SSA_GUI_v%APP_VERSION%_windows_amd64.exe --windows-console-mode=disable --windows-icon-from-ico=resources/app_icon.ico launchers/gui_entry.py
)

if errorlevel 1 (
    echo Build Nuitka GUI falhou. Veja o log: "%LOG_FILE%"
    if "%SILENT%"=="0" pause
    exit /b 1
)

if "%SILENT%"=="1" (
    call %BASE_CMD% --output-filename=SSA_CLI_v%APP_VERSION%_windows_amd64.exe --windows-console-mode=force launchers/cli_entry.py >> "%LOG_FILE%" 2>&1
) else (
    call %BASE_CMD% --output-filename=SSA_CLI_v%APP_VERSION%_windows_amd64.exe --windows-console-mode=force launchers/cli_entry.py
)

if errorlevel 1 (
    echo Build Nuitka CLI falhou. Veja o log: "%LOG_FILE%"
    if "%SILENT%"=="0" pause
    exit /b 1
)

if "%WITH_LOCAL_DATA%"=="1" (
    if "%SILENT%"=="1" (
        uv run --python 3.13 "%REPO_ROOT%\scripts\copy_data_to_builds.py" --build-system nuitka --allow-local-data >> "%LOG_FILE%" 2>&1
    ) else (
        uv run --python 3.13 "%REPO_ROOT%\scripts\copy_data_to_builds.py" --build-system nuitka --allow-local-data
    )

    if errorlevel 1 (
        echo Build Nuitka concluiu, mas copia de dados falhou. Veja o log: "%LOG_FILE%"
        if "%SILENT%"=="0" pause
        exit /b 1
    )
) else (
    if "%SILENT%"=="1" (
        echo [build_nuitka] pulando copia de dados locais. Use --with-local-data para habilitar. >> "%LOG_FILE%"
    ) else (
        echo INFO Pulando copia de dados locais. Use --with-local-data para habilitar.
    )
)

echo Build Nuitka concluido com sucesso.
echo Artefatos em: "%REPO_ROOT%\builds\nuitka\windows_amd64"
if "%SILENT%"=="0" (
    set /p "DO_CLEANUP=Executar cleanup TEMP agora? [s/N]: "
    if /I "!DO_CLEANUP!"=="s" (
        uv run --python 3.13 "%REPO_ROOT%\scripts\cleanup_build_artifacts.py" --scope temp
    )
)
if "%SILENT%"=="0" pause
exit /b 0
