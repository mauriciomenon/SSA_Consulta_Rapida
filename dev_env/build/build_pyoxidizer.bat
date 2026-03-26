@echo off
setlocal EnableExtensions EnableDelayedExpansion
REM Build script PyOxidizer (windows_amd64) com uv/python 3.13.

set "SILENT=0"
if /I "%~1"=="--silent" set "SILENT=1"

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
set "UV_MANAGED_PYTHON=true"
set "UV_PROJECT_ENVIRONMENT=.venv-win"

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
        set "RUSTFLAGS=-Clinker=%MSVC_LINK%"
        if "%SILENT%"=="0" echo Linker MSVC for?ado: "%MSVC_LINK%"
    )
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
set "STAGE_DIR_POSIX=%STAGE_DIR:\=/%"

if "%SILENT%"=="1" (
    echo [build_pyoxidizer] modo silencioso ativo. log: "%LOG_FILE%"
    uv tool run --python 3.13 --from pyoxidizer pyoxidizer build --release --var SSA_PROJECT_ROOT "%STAGE_DIR_POSIX%" --path "%STAGE_DIR%" > "%LOG_FILE%" 2>&1
) else (
    echo Iniciando build PyOxidizer...
    uv tool run --python 3.13 --from pyoxidizer pyoxidizer build --release --var SSA_PROJECT_ROOT "%STAGE_DIR_POSIX%" --path "%STAGE_DIR%"
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

if "%SILENT%"=="1" (
    set "UV_PROJECT_ENVIRONMENT=.venv-pyoxidizer-runtime-win"
    uv run --python 3.10 --with numpy --with pandas --with tabulate --with openpyxl --with pyqt6 python "%REPO_ROOT%\scripts\sync_pyoxidizer_runtime_libs.py" --target "%TARGET_BUILD_DIR%\lib" >> "%LOG_FILE%" 2>&1
    set "UV_PROJECT_ENVIRONMENT=.venv-win"
) else (
    set "UV_PROJECT_ENVIRONMENT=.venv-pyoxidizer-runtime-win"
    uv run --python 3.10 --with numpy --with pandas --with tabulate --with openpyxl --with pyqt6 python "%REPO_ROOT%\scripts\sync_pyoxidizer_runtime_libs.py" --target "%TARGET_BUILD_DIR%\lib"
    set "UV_PROJECT_ENVIRONMENT=.venv-win"
)

if errorlevel 1 (
    echo Build PyOxidizer concluiu, mas sync de runtime libs falhou. Veja o log: "%LOG_FILE%"
    if "%SILENT%"=="0" pause
    exit /b 1
)

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
