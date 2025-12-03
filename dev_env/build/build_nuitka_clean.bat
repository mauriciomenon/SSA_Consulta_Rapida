@echo off
REM Build script para Nuitka sem gcc do MSYS2 no PATH

echo Removendo MSYS2/MinGW do PATH temporariamente...
echo.

REM Salvar PATH original
set "PATH_BACKUP=%PATH%"

REM PATH limpo sem MSYS2
set "PATH=C:\Windows\System32;C:\Windows;C:\Users\menon\.pyenv\pyenv-win\bin;C:\Users\menon\.pyenv\pyenv-win\shims;C:\Users\menon\scoop\shims"

echo PATH limpo configurado
echo.

REM Limpar build anterior se existir
if exist build\nuitka rmdir /s /q build\nuitka

echo Iniciando build com Nuitka...
echo Nuitka vai baixar seu proprio compilador MinGW64 na primeira vez.
echo Isso vai demorar 5-15 minutos na primeira vez.
echo.

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
    echo Executavel em: build\nuitka\main.dist\main.exe
) else (
    echo Build falhou com erro %ERRORLEVEL%
)

REM Restaurar PATH original
set "PATH=%PATH_BACKUP%"
echo.
echo PATH restaurado

pause
