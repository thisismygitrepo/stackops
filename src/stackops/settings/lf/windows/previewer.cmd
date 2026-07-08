@echo off
pwsh -NoLogo -NoProfile -File "%~dp0previewer.ps1" %*
exit /b %ERRORLEVEL%
