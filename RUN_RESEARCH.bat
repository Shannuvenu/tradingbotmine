@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo [INDIA QUANT] Virtual environment not found. Run INSTALL_WINDOWS.bat first.
  pause
  exit /b 1
)
set PY=.venv\Scripts\python.exe
%PY% -m indiaquant.cli research
pause
