@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo [INDIA QUANT] Virtual environment not found. Run INSTALL_WINDOWS.bat first.
  pause
  exit /b 1
)
set PY=.venv\Scripts\python.exe
%PY% -m indiaquant.cli sync-instruments --exchange NSE BSE
%PY% -m indiaquant.cli sync-holidays
%PY% -m indiaquant.cli fetch-history --interval 1d --days 1825
%PY% -m indiaquant.cli fetch-history --interval 1m --days 120
pause
