@echo off
REM Build script usando PyInstaller

echo Iniciando build com PyInstaller...
echo Previsão: 2-5 minutos.
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
    echo.
    echo === COPIANDO PARA BUILDS/PYINSTALLER ===
    if exist builds\pyinstaller rmdir /s /q builds\pyinstaller
    mkdir builds\pyinstaller
    xcopy /E /I /Y dist\SSA_Consulta_Rapida builds\pyinstaller
    echo Copiado para: builds\pyinstaller
    echo.
    echo === COPIANDO DADOS (DB E EXCEL) ===
    python scripts\copy_data_to_builds.py --build-system pyinstaller
) else (
    echo Build falhou com erro %ERRORLEVEL%
)

pause
