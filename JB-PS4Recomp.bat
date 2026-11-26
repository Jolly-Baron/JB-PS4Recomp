@echo off
rem JB PS4Recomp launcher starter. Copyright (c) 2026 Jolly Baron. GPL-2.0-or-later.
setlocal
cd /d "%~dp0"
if exist "python\pythonw.exe" (
    start "" "python\pythonw.exe" launcher.py %*
    goto :eof
)
where pyw >nul 2>nul
if %ERRORLEVEL% equ 0 ( start "" pyw -3 launcher.py %* & goto :eof )
where pythonw >nul 2>nul
if %ERRORLEVEL% equ 0 ( start "" pythonw launcher.py %* & goto :eof )
python launcher.py %*
if errorlevel 1 pause
endlocal
