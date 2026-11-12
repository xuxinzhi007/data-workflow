@echo off
rem Windows entry: bypass ExecutionPolicy, run install.ps1, which launches Git Bash + install.sh.
rem Same flags as install.sh. Run from the target repo root:
rem   <data-workflow>\scripts\install.cmd [--project] [--with-hooks] [--unlink]
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
exit /b %ERRORLEVEL%
