@echo off
setlocal EnableExtensions EnableDelayedExpansion
REM Build script PyOxidizer (windows_amd64) com uv/python 3.13.

set "SILENT=0"
set "WITH_LOCAL_DATA=0"
for %%A in (%*) do (
    if /I "%%~A"=="--silent" set "SILENT=1"
    if /I "%%~A"=="--with-local-data" set "WITH_LOCAL_DATA=1"
)

for %%I in ("%~dp0..\..") do set "REPO_ROOT=%%~fI"
set "LOG_DIR=%REPO_ROOT%\launchers\logs"
set "LOG_FILE=%LOG_DIR%\build_pyoxidizer_windows_amd64.log"
set "TARGET_BUILD_DIR=%REPO_ROOT%\builds\pyoxidizer\windows_amd64"
set "STAGE_DIR=%REPO_ROOT%\build\pyoxidizer_stage_windows_amd64"
set "XCOPY_EXE=C:\Windows\System32\xcopy.exe"
set "ROBOCOPY_EXE=C:\Windows\System32\robocopy.exe"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
if not exist "%REPO_ROOT%\builds\pyoxidizer" mkdir "%REPO_ROOT%\builds\pyoxidizer"

set "UV_PYTHON=3.13"
REM PyOxidizer embeds CPython 3.10 on this target; native runtime libs must match it.
set "PYOX_RUNTIME_PYTHON=3.10"
if not defined PYOXIDIZER_UV_PACKAGE set "PYOXIDIZER_UV_PACKAGE=pyoxidizer==0.24.0"
set "UV_MANAGED_PYTHON=true"
set "UV_PROJECT_ENVIRONMENT=.venv-win"

for /f "tokens=1,2 delims=|" %%A in ('uv run --python 3.13 python -c "import json,pathlib,re; v=str(json.loads(pathlib.Path('config/version.json').read_text(encoding='utf-8')).get('version_short','')).strip(); assert v, 'version_short ausente'; parts=[int(p) for p in re.findall(r'\d+', v)[:4]]; parts=(parts+[0,0,0,0])[:4]; print(v+'|'+'.'.join(str(p) for p in parts))"') do (
    set "APP_VERSION=%%A"
    set "APP_VERSION_PE=%%B"
)
if not defined APP_VERSION (
    echo Erro ao carregar versao de config\version.json.
    exit /b 1
)
if not defined APP_VERSION_PE (
    echo Erro ao calcular product version de config\version.json.
    exit /b 1
)

set "MSVC_LINK="
set "VCVARS="
set "VSWHERE=C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"

if exist "%VSWHERE%" (
    for /f "usebackq delims=" %%P in (`"%VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do (
        if exist "%%P\VC\Auxiliary\Build\vcvars64.bat" set "VCVARS=%%P\VC\Auxiliary\Build\vcvars64.bat"
    )
)

if not defined VCVARS (
    for %%V in (18 2022 17 16) do (
        for %%E in (BuildTools Community Professional Enterprise) do (
            if not defined VCVARS if exist "C:\Program Files\Microsoft Visual Studio\%%V\%%E\VC\Auxiliary\Build\vcvars64.bat" set "VCVARS=C:\Program Files\Microsoft Visual Studio\%%V\%%E\VC\Auxiliary\Build\vcvars64.bat"
            if not defined VCVARS if exist "C:\Program Files (x86)\Microsoft Visual Studio\%%V\%%E\VC\Auxiliary\Build\vcvars64.bat" set "VCVARS=C:\Program Files (x86)\Microsoft Visual Studio\%%V\%%E\VC\Auxiliary\Build\vcvars64.bat"
        )
    )
)

if not defined VCVARS (
    echo Erro: vcvars64.bat nao encontrado. Instale Visual Studio Build Tools com workload C++.
    echo Dica: caminho esperado exemplo: C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat
    exit /b 1
)

if "%SILENT%"=="1" (
    call "%VCVARS%" >nul 2>&1
) else (
    echo Configurando ambiente MSVC: "%VCVARS%"
    call "%VCVARS%"
)

if errorlevel 1 (
    echo Erro ao inicializar ambiente MSVC via vcvars64.bat.
    exit /b 1
)

if defined VCToolsInstallDir (
    set "MSVC_LINK=%VCToolsInstallDir%bin\Hostx64\x64\link.exe"
    if exist "%MSVC_LINK%" (
        set "PATH=%VCToolsInstallDir%bin\Hostx64\x64;%PATH%"
        set "CARGO_TARGET_X86_64_PC_WINDOWS_MSVC_LINKER=%MSVC_LINK%"
        if "%SILENT%"=="0" echo Linker MSVC forcado: "%MSVC_LINK%"
    )
)

if not defined MSVC_LINK (
    for /f "delims=" %%L in ('where link.exe 2^>nul') do (
        if not defined MSVC_LINK set "MSVC_LINK=%%L"
    )
)

if not defined MSVC_LINK (
    echo Erro: linker MSVC nao localizado. link.exe atual no PATH pode nao ser do Visual Studio.
    exit /b 1
)

if not exist "%MSVC_LINK%" (
    echo Erro: linker MSVC nao localizado. link.exe atual no PATH pode nao ser do Visual Studio.
    exit /b 1
)

set "WINSDK_LIB="
set "WINSDK_INC="
for /f "delims=" %%D in ('dir /b /ad "C:\Program Files (x86)\Windows Kits\10\Lib\*" 2^>nul ^| C:\Windows\System32\sort.exe /r') do (
    if not defined WINSDK_LIB set "WINSDK_LIB=C:\Program Files (x86)\Windows Kits\10\Lib\%%D"
)
for /f "delims=" %%D in ('dir /b /ad "C:\Program Files (x86)\Windows Kits\10\Include\*" 2^>nul ^| C:\Windows\System32\sort.exe /r') do (
    if not defined WINSDK_INC set "WINSDK_INC=C:\Program Files (x86)\Windows Kits\10\Include\%%D"
)
if defined WINSDK_LIB (
    if exist "%WINSDK_LIB%\um\x64\kernel32.lib" (
        set "LIB=%WINSDK_LIB%\um\x64;%WINSDK_LIB%\ucrt\x64;%LIB%"
        if "%SILENT%"=="0" echo Windows SDK LIB: "%WINSDK_LIB%"
    )
)
if defined WINSDK_INC (
    set "INCLUDE=%WINSDK_INC%\um;%WINSDK_INC%\ucrt;%WINSDK_INC%\shared;%WINSDK_INC%\winrt;%INCLUDE%"
    if "%SILENT%"=="0" echo Windows SDK INCLUDE: "%WINSDK_INC%"
)

set "COPY_TOOL="
if exist "%XCOPY_EXE%" set "COPY_TOOL=xcopy"
if not defined COPY_TOOL if exist "%ROBOCOPY_EXE%" set "COPY_TOOL=robocopy"
if not defined COPY_TOOL (
    echo Erro: nem xcopy nem robocopy foram encontrados em C:\Windows\System32.
    exit /b 1
)

if exist "%STAGE_DIR%" (
    rmdir /s /q "%STAGE_DIR%" >nul 2>&1
    if exist "%STAGE_DIR%" (
        echo Erro: nao foi possivel limpar staging "%STAGE_DIR%". Feche processos que usam esta pasta e tente novamente.
        exit /b 1
    )
)
mkdir "%STAGE_DIR%"
copy /Y "%REPO_ROOT%\pyoxidizer.bzl" "%STAGE_DIR%\pyoxidizer.bzl" >nul
if errorlevel 1 (
    echo Erro ao copiar "pyoxidizer.bzl" para staging.
    exit /b 1
)
copy /Y "%REPO_ROOT%\main.py" "%STAGE_DIR%\main.py" >nul
if errorlevel 1 (
    echo Erro ao copiar "main.py" para staging.
    exit /b 1
)
for %%D in (core gui armazenamento extracao utils interface exportacao shared config resources themes) do (
    if exist "%REPO_ROOT%\%%D" (
        if /I "%COPY_TOOL%"=="xcopy" (
            "%XCOPY_EXE%" /E /I /Y "%REPO_ROOT%\%%D\*" "%STAGE_DIR%\%%D\" >nul
            set "XCOPY_RC=!ERRORLEVEL!"
            if !XCOPY_RC! GEQ 2 (
                echo Erro ao copiar "%%D" para staging via xcopy. Codigo: !XCOPY_RC!
                exit /b 1
            )
        ) else (
            "%ROBOCOPY_EXE%" "%REPO_ROOT%\%%D" "%STAGE_DIR%\%%D" /E /NFL /NDL /NJH /NJS /NP >nul
            set "ROBO_RC=!ERRORLEVEL!"
            if !ROBO_RC! GEQ 8 (
                echo Erro ao copiar "%%D" para staging via robocopy. Codigo: !ROBO_RC!
                exit /b 1
            )
        )
    )
)
if not exist "%STAGE_DIR%\docs" mkdir "%STAGE_DIR%\docs"
copy /Y "%REPO_ROOT%\docs\GUIA_MIGRACAO_NOVA_INSTALACAO.md" "%STAGE_DIR%\docs\GUIA_MIGRACAO_NOVA_INSTALACAO.md" >nul
if errorlevel 1 (
    echo Erro ao copiar guia de instalacao para staging.
    exit /b 1
)
if not exist "%STAGE_DIR%\config" mkdir "%STAGE_DIR%\config"
set "BUILD_INFO_FILE=%STAGE_DIR%\config\build_info.json"
uv run --python 3.13 "%REPO_ROOT%\dev_env\build\write_build_info.py" --repo-root "%REPO_ROOT%" --output "%BUILD_INFO_FILE%" --build-system pyoxidizer --platform windows_amd64 --app-version "%APP_VERSION%"
if errorlevel 1 (
    echo Erro ao gerar build_info.json para staging.
    exit /b 1
)
set "STAGE_DIR_POSIX=%STAGE_DIR:\=/%"
uv tool run --python 3.13 --from "%PYOXIDIZER_UV_PACKAGE%" pyoxidizer --version >nul 2>&1
if errorlevel 1 (
    echo Erro: PyOxidizer indisponivel via uv tool: "%PYOXIDIZER_UV_PACKAGE%"
    exit /b 1
)

if "%SILENT%"=="1" (
    echo [build_pyoxidizer] modo silencioso ativo. log: "%LOG_FILE%"
    uv tool run --python 3.13 --from "%PYOXIDIZER_UV_PACKAGE%" pyoxidizer build --release --var SSA_PROJECT_ROOT "%STAGE_DIR_POSIX%" --path "%STAGE_DIR%" > "%LOG_FILE%" 2>&1
) else (
    echo Iniciando build PyOxidizer...
    uv tool run --python 3.13 --from "%PYOXIDIZER_UV_PACKAGE%" pyoxidizer build --release --var SSA_PROJECT_ROOT "%STAGE_DIR_POSIX%" --path "%STAGE_DIR%"
)

if errorlevel 1 (
    echo Build PyOxidizer falhou. Veja o log: "%LOG_FILE%"
    if "%SILENT%"=="0" pause
    exit /b 1
)

set "SOURCE_INSTALL=%STAGE_DIR%\build\x86_64-pc-windows-msvc\release\install"
if not exist "%SOURCE_INSTALL%" (
    echo Build PyOxidizer concluiu, mas pasta install nao foi encontrada: "%SOURCE_INSTALL%"
    if "%SILENT%"=="0" pause
    exit /b 1
)

if not exist "%TARGET_BUILD_DIR%" (
    mkdir "%TARGET_BUILD_DIR%"
    if errorlevel 1 (
        echo Erro ao criar target "%TARGET_BUILD_DIR%".
        exit /b 1
    )
) else (
    for /d %%D in ("%TARGET_BUILD_DIR%\*") do (
        rmdir /s /q "%%~fD" >nul 2>&1
    )
    for %%F in ("%TARGET_BUILD_DIR%\*") do (
        del /f /q "%%~fF" >nul 2>&1
    )
)
if /I "%COPY_TOOL%"=="xcopy" (
    "%XCOPY_EXE%" /E /I /Y "%SOURCE_INSTALL%\*" "%TARGET_BUILD_DIR%\" >nul
    set "XCOPY_RC=!ERRORLEVEL!"
    if !XCOPY_RC! GEQ 2 (
        echo Erro ao copiar install para target via xcopy. Codigo: !XCOPY_RC!
        exit /b 1
    )
) else (
    "%ROBOCOPY_EXE%" "%SOURCE_INSTALL%" "%TARGET_BUILD_DIR%" /E /NFL /NDL /NJH /NJS /NP >nul
    set "ROBO_RC=!ERRORLEVEL!"
    if !ROBO_RC! GEQ 8 (
        echo Erro ao copiar install para target via robocopy. Codigo: !ROBO_RC!
        exit /b 1
    )
)

if not exist "%TARGET_BUILD_DIR%\config" mkdir "%TARGET_BUILD_DIR%\config"
copy /Y "%REPO_ROOT%\config\version.json" "%TARGET_BUILD_DIR%\config\version.json" >nul
if errorlevel 1 (
    echo Build PyOxidizer concluiu, mas copia de config/version.json falhou.
    exit /b 1
)

set "RCEDIT_EXE="
for /f "delims=" %%R in ('where rcedit.exe 2^>nul') do (
    if not defined RCEDIT_EXE set "RCEDIT_EXE=%%R"
)
if not defined RCEDIT_EXE (
    echo Erro: rcedit.exe nao encontrado. Instale com: scoop install rcedit
    exit /b 1
)
set "APP_ICON=%REPO_ROOT%\resources\app_icon.ico"
if not exist "%APP_ICON%" (
    echo Erro: icone do aplicativo nao encontrado: "%APP_ICON%"
    exit /b 1
)
"%RCEDIT_EXE%" "%TARGET_BUILD_DIR%\SSA_Consulta_Rapida.exe" --set-icon "%APP_ICON%"
if errorlevel 1 (
    echo Build PyOxidizer concluiu, mas aplicacao do icone falhou.
    exit /b 1
)
"%RCEDIT_EXE%" "%TARGET_BUILD_DIR%\SSA_Consulta_Rapida.exe" ^
    --set-file-version "%APP_VERSION_PE%" ^
    --set-product-version "%APP_VERSION_PE%" ^
    --set-version-string "CompanyName" "SSA Consulta Rapida" ^
    --set-version-string "FileDescription" "SSA_Consulta_Rapida.exe" ^
    --set-version-string "InternalName" "SSA_Consulta_Rapida" ^
    --set-version-string "OriginalFilename" "SSA_Consulta_Rapida.exe" ^
    --set-version-string "ProductName" "SSA Consulta Rapida" ^
    --set-version-string "ProductVersion" "%APP_VERSION_PE%"
if errorlevel 1 (
    echo Build PyOxidizer concluiu, mas aplicacao de metadata falhou.
    exit /b 1
)

if "%SILENT%"=="1" (
    set "UV_PROJECT_ENVIRONMENT=.venv-pyoxidizer-runtime-win"
    uv run --python %PYOX_RUNTIME_PYTHON% --with numpy --with pandas --with tabulate --with openpyxl --with pyqt6 python "%REPO_ROOT%\scripts\sync_pyoxidizer_runtime_libs.py" --target "%TARGET_BUILD_DIR%\lib" >> "%LOG_FILE%" 2>&1
    set "UV_PROJECT_ENVIRONMENT=.venv-win"
) else (
    set "UV_PROJECT_ENVIRONMENT=.venv-pyoxidizer-runtime-win"
    uv run --python %PYOX_RUNTIME_PYTHON% --with numpy --with pandas --with tabulate --with openpyxl --with pyqt6 python "%REPO_ROOT%\scripts\sync_pyoxidizer_runtime_libs.py" --target "%TARGET_BUILD_DIR%\lib"
    set "UV_PROJECT_ENVIRONMENT=.venv-win"
)

if errorlevel 1 (
    echo Build PyOxidizer concluiu, mas sync de runtime libs falhou. Veja o log: "%LOG_FILE%"
    if "%SILENT%"=="0" pause
    exit /b 1
)

if "%WITH_LOCAL_DATA%"=="1" (
    if "%SILENT%"=="1" (
        uv run --python 3.13 "%REPO_ROOT%\scripts\copy_data_to_builds.py" --build-system pyoxidizer --allow-local-data >> "%LOG_FILE%" 2>&1
    ) else (
        uv run --python 3.13 "%REPO_ROOT%\scripts\copy_data_to_builds.py" --build-system pyoxidizer --allow-local-data
    )

    if errorlevel 1 (
        echo Build PyOxidizer concluiu, mas copia de dados falhou. Veja o log: "%LOG_FILE%"
        if "%SILENT%"=="0" pause
        exit /b 1
    )
) else (
    if "%SILENT%"=="1" (
        echo [build_pyoxidizer] pulando copia de dados locais. Use --with-local-data para habilitar.>> "%LOG_FILE%"
    ) else (
        echo INFO Pulando copia de dados locais. Use --with-local-data para habilitar.
    )
)

set "SSA_PYOXIDIZER_SMOKE_LOG=%TEMP%\ssa_pyoxidizer_windows_amd64_smoke.log"
set "PYOXIDIZER_EXE=%TARGET_BUILD_DIR%\SSA_Consulta_Rapida.exe"
uv run --python 3.13 python "%REPO_ROOT%\scripts\smoke_cli.py" --executable "%PYOXIDIZER_EXE%" --json > "%SSA_PYOXIDIZER_SMOKE_LOG%" 2>&1
if errorlevel 1 (
    echo Smoke PyOxidizer falhou. Veja: "%SSA_PYOXIDIZER_SMOKE_LOG%"
    exit /b 1
)

echo Build PyOxidizer concluido com sucesso.
echo Artefatos em: "%TARGET_BUILD_DIR%"
if "%SILENT%"=="0" (
    set /p "DO_CLEANUP=Executar cleanup TEMP agora? [s/N]: "
    if /I "!DO_CLEANUP!"=="s" (
        uv run --python 3.13 "%REPO_ROOT%\scripts\cleanup_build_artifacts.py" --scope temp
    )
)
if "%SILENT%"=="0" pause
exit /b 0
