@echo off
setlocal
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
