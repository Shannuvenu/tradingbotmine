@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo [INDIA QUANT] Virtual environment not found. Run INSTALL_WINDOWS.bat first.
  pause
  exit /b 1
)
set PY=.venv\Scripts\python.exe
if not exist logs mkdir logs
(%PY% -m indiaquant.cli validate-config & %PY% -m indiaquant.cli health) > logs\health.txt 2>&1
type logs\health.txt
echo HEALTH_DONE>>logs\health.txt
pause
