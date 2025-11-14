@echo off
REM Build script usando PyInstaller

echo Iniciando build com PyInstaller...
echo Isso vai demorar 2-5 minutos.
echo.

REM Limpar build anterior se existir
if exist build\pyinstaller rmdir /s /q build\pyinstaller
if exist dist\SSA_Consulta_Rapida rmdir /s /q dist\SSA_Consulta_Rapida

REM Build com PyInstaller
pyinstaller ^
    --name="SSA_Consulta_Rapida" ^
    --console ^
    --onedir ^
    --add-data="config;config" ^
    --hidden-import=pandas ^
    --hidden-import=openpyxl ^
    --hidden-import=PyQt6 ^
    --hidden-import=PyQt6.QtCore ^
    --hidden-import=PyQt6.QtGui ^
    --hidden-import=PyQt6.QtWidgets ^
    --hidden-import=numpy ^
    --collect-all=pandas ^
    --collect-all=numpy ^
    --noconfirm ^
    main.py

echo.
if %ERRORLEVEL% EQU 0 (
    echo Build concluido com sucesso!
    echo Executavel em: dist\SSA_Consulta_Rapida\SSA_Consulta_Rapida.exe
) else (
    echo Build falhou com erro %ERRORLEVEL%
)

pause
