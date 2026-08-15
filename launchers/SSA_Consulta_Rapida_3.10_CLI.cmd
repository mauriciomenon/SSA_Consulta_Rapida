@echo off
setlocal
rem Launcher CLI: inicia a aplicacao no modo CLI sem exigir ativacao manual

for %%I in ("%~dp0..") do set "ROOT=%%~fI"
pushd "%ROOT%"

rem Preferir Python da venv local, se existir
set "PYEXE="
if exist ".venv_build\Scripts\python.exe" set "PYEXE=.venv_build\Scripts\python.exe"
if not defined PYEXE if exist ".venv\Scripts\python.exe" set "PYEXE=.venv\Scripts\python.exe"
if not defined PYEXE set "PYEXE=py"

"%PYEXE%" main.py %*
set ERR=%ERRORLEVEL%
popd
exit /b %ERR%
