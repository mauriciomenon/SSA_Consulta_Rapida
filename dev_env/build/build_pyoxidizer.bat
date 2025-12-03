@echo off
REM Script para buildar com PyOxidizer usando MSVC correto

echo Configurando ambiente Visual Studio 2022...

REM Limpar PATH para remover conflitos com Git
set "PATH_BACKUP=%PATH%"
set "PATH=C:\Windows\System32;C:\Windows;C:\Users\menon\.pyenv\pyenv-win\bin;C:\Users\menon\.pyenv\pyenv-win\shims"

REM Configurar ambiente MSVC
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"

echo.
echo Verificando variaveis de ambiente...
echo LIB=%LIB%
echo.
echo INCLUDE=%INCLUDE%
echo.
echo Iniciando build com PyOxidizer...
echo Isso vai demorar 10-30 minutos na primeira vez.
echo.

pyoxidizer.bat build --release

echo.
if %ERRORLEVEL% EQU 0 (
    echo Build concluido com sucesso!
    echo Resultado em: build\x86_64-pc-windows-msvc\release\install\
) else (
    echo Build falhou com erro %ERRORLEVEL%
)

REM Restaurar PATH original
set "PATH=%PATH_BACKUP%"

pause
