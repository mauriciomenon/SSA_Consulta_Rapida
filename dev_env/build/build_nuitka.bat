@echo off
REM Build script usando Nuitka

echo Iniciando build com Nuitka...
echo Nuitka vai baixar seu proprio compilador MinGW64 na primeira vez.
echo Isso vai demorar 5-15 minutos na primeira vez.
echo.

REM Limpar build anterior se existir
if exist build\nuitka rmdir /s /q build\nuitka

REM Build com Nuitka
python -m nuitka ^
    --standalone ^
    --assume-yes-for-downloads ^
    --windows-console-mode=force ^
    --enable-plugin=pyqt6 ^
    --include-data-dir=config=config ^
    --output-dir=build\nuitka ^
    --company-name="SSA" ^
    --product-name="SSA Consulta Rapida" ^
    --file-version=4.0.0 ^
    --product-version=4.0.0 ^
    --follow-imports ^
    main.py

echo.
if %ERRORLEVEL% EQU 0 (
    echo Build concluido com sucesso!
    echo Executavel em: build\nuitka\SSA_Consulta_Rapida.exe
) else (
    echo Build falhou com erro %ERRORLEVEL%
)

pause
