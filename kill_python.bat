@echo off
echo Finalizando todos os processos Python...
taskkill /F /IM python.exe /T 2>nul
if %errorlevel% equ 0 (
    echo [OK] Processos Python finalizados
) else (
    echo [INFO] Nenhum processo Python rodando
)
timeout /t 2 /nobreak >nul
echo.
echo Verificando porta 51234...
netstat -ano | findstr :51234 >nul
if %errorlevel% equ 0 (
    echo [AVISO] Porta 51234 ainda em uso
    echo Aguardando TIME_WAIT...
    timeout /t 3 /nobreak >nul
) else (
    echo [OK] Porta 51234 livre
)
echo.
echo ===================================
echo PRONTO! Execute:
echo   python main.py --gui
echo ===================================
