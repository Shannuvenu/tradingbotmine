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
echo Running strategy research on downloaded data (no orders; several minutes)...
%PY% -W ignore -m indiaquant.cli research > logs\research.txt 2>&1
type logs\research.txt
echo RESEARCH_DONE>>logs\research.txt
pause
