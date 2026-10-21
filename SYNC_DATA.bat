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
echo Downloading instruments, holidays and price history (read-only, several minutes)...
(%PY% -m indiaquant.cli sync-instruments --exchange NSE BSE
 %PY% -m indiaquant.cli sync-holidays
 %PY% -m indiaquant.cli fetch-history --interval 1d --days 1825
 %PY% -m indiaquant.cli fetch-history --interval 1m --days 120) > logs\sync.txt 2>&1
type logs\sync.txt
echo SYNC_DONE>>logs\sync.txt
pause
