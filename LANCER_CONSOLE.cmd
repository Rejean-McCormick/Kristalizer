@echo off
setlocal
rem Force UTF-8 for Python subprocess output and cmd.exe Unicode display.
chcp 65001 >nul 2>&1
set "PYTHONIOENCODING=utf-8:replace"
set "PYTHONUTF8=1"
set "KRISTALIZER_UTF8=1"
cd /d "%~dp0"
where py >nul 2>&1
if %errorlevel%==0 (
  py -3 kristalizer.py --help
) else (
  python kristalizer.py --help
)
pause
