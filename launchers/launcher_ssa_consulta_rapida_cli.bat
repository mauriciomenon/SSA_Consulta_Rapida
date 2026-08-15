@echo off
setlocal
rem Launcher CLI for the packaged PyInstaller executable.

for %%I in ("%~dp0..") do set "ROOT=%%~fI"
set "EXE=%ROOT%\builds\pyinstaller\windows_amd64\SSA_Consulta_Rapida.exe"
if not exist "%EXE%" set "EXE=%ROOT%\builds\pyinstaller\SSA_Consulta_Rapida.exe"
if not exist "%EXE%" (
    echo PyInstaller executable not found. Build it before running this launcher.
    exit /b 1
)

"%EXE%" %*
exit /b %ERRORLEVEL%
