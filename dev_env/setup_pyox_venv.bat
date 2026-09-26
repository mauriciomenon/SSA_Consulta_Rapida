@echo off
REM Setup virtual environment for PyOxidizer to read from

echo Creating virtual environment...
cd /d "%~dp0.." || exit /b 1
where uv > nul 2>&1
if errorlevel 1 (
    echo Erro: uv nao encontrado no PATH.
    exit /b 1
)
if not exist pyox_venv (
    uv venv --python python pyox_venv
    if errorlevel 1 (
        echo Erro ao criar ambiente PyOxidizer.
        exit /b 1
    )
)
if not exist pyox_venv\Scripts\python.exe (
    echo Erro: ambiente PyOxidizer incompleto.
    exit /b 1
)
if not exist pyox_venv\Scripts\activate.bat (
    echo Erro: script de ativacao PyOxidizer ausente.
    exit /b 1
)

echo Activating virtual environment...
call pyox_venv\Scripts\activate.bat
if errorlevel 1 exit /b 1

echo Installing dependencies...
uv pip install --python "%CD%\pyox_venv\Scripts\python.exe" pandas==2.3.3 openpyxl==3.1.5 PyQt6==6.10.0
if errorlevel 1 (
    echo Erro ao instalar dependencias PyOxidizer com uv.
    exit /b 1
)

echo.
echo Virtual environment ready at: pyox_venv
echo PyOxidizer will read packages from this environment.
echo.

pause
