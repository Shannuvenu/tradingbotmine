@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo [INDIA QUANT] Virtual environment not found. Run INSTALL_WINDOWS.bat first.
  pause
  exit /b 1
)
set PY=.venv\Scripts\python.exe
echo Halting trading and cancelling pending orders (positions are NOT closed).
%PY% -m indiaquant.cli kill --reason "KILL_SWITCH.bat"
echo.
set /p FL=Also LIQUIDATE all long positions with marketable limit sells? Type YES to confirm: 
if /I "%FL%"=="YES" %PY% -m indiaquant.cli kill --flatten --reason "KILL_SWITCH.bat liquidation"
echo The KILL file stays in this folder until you delete it deliberately.
pause
