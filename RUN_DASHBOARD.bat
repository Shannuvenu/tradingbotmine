@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo [INDIA QUANT] Virtual environment not found. Run INSTALL_WINDOWS.bat first.
  pause
  exit /b 1
)
set PY=.venv\Scripts\python.exe
echo Starting dashboard on http://127.0.0.1:8501  (local only; close this window to stop)
%PY% -m streamlit run dashboard\app.py --server.address 127.0.0.1 --server.port 8501
pause
