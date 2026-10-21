@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo [INDIA QUANT] Virtual environment not found. Run INSTALL_WINDOWS.bat first.
  pause
  exit /b 1
)
set PY=.venv\Scripts\python.exe
echo ==================================================================
echo  Engine loop. Orders are sent ONLY if state is LIVE_ACTIVE for today.
echo  Stop: Ctrl+C here, or double-click KILL_SWITCH.bat (halts + cancels pending).
echo  Orders must originate from your registered static IP.
echo ==================================================================
%PY% -m indiaquant.cli status
%PY% -m indiaquant.cli run --interval 60
pause
