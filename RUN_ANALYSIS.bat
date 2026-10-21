@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo [INDIA QUANT] Virtual environment not found. Run INSTALL_WINDOWS.bat first.
  pause
  exit /b 1
)
set PY=.venv\Scripts\python.exe
echo Analysis cycle: signals and risk decisions are logged; NO orders unless LIVE_ACTIVE.
%PY% -m indiaquant.cli analyze
pause
