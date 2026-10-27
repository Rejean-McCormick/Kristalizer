@echo off
setlocal
rem Force UTF-8 for Python subprocess output and cmd.exe Unicode display.
chcp 65001 >nul 2>&1
set "PYTHONIOENCODING=utf-8:replace"
set "PYTHONUTF8=1"
set "KRISTALIZER_UTF8=1"
cd /d "%~dp0"
where pyw >nul 2>&1
if %errorlevel%==0 (
  start "Kristalizer" pyw -3 "%~dp0Kristalizer.pyw"
  exit /b 0
)
where pythonw >nul 2>&1
if %errorlevel%==0 (
  start "Kristalizer" pythonw "%~dp0Kristalizer.pyw"
  exit /b 0
)
echo Python 3 et Tkinter requis. Voir README.md
pause
exit /b 1
