@echo off
setlocal EnableExtensions
REM Legacy wrapper mantido para compatibilidade.
call "%~dp0build_nuitka_clean.bat" %*
exit /b %ERRORLEVEL%
