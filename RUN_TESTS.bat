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
%PY% -m indiaquant.cli init
%PY% -m pytest -q tests > logs\test_results.txt 2>&1
set RC=%errorlevel%
type logs\test_results.txt
if not "%RC%"=="0" (echo TESTS FAILED) else (echo ALL TESTS PASSED)
pause
