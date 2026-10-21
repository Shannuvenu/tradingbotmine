@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo  INDIA QUANT - Windows installer (no orders are placed)
echo ============================================================
where py >nul 2>nul
if %errorlevel%==0 (set BASEPY=py -3) else (set BASEPY=python)
%BASEPY% -c "import sys; assert sys.version_info>=(3,11), sys.version; print('Python', sys.version)" || (
  echo Python 3.11+ 64-bit is required. Install from https://www.python.org/downloads/windows/ and tick "Add to PATH".
  pause & exit /b 1)
if not exist ".venv\Scripts\python.exe" %BASEPY% -m venv .venv || (echo venv creation failed & pause & exit /b 1)
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo Some packages failed. Retrying core packages without the optional Upstox SDK...
  .venv\Scripts\python.exe -m pip install "numpy>=1.26,<3" "pandas>=2.2,<4" "scipy>=1.11,<2" "scikit-learn>=1.4,<2" "requests>=2.31,<3" "streamlit>=1.46,<2" "plotly>=5.20,<7" "pytest>=8.0"
)
if not exist ".env" copy ".env.example" ".env" >nul && echo Created .env from template (fill it in at the FINAL STEP).
.venv\Scripts\python.exe -m indiaquant.cli init
.venv\Scripts\python.exe -m indiaquant.cli validate-config
echo.
echo Done. Next: RUN_TESTS.bat, then RUN_DASHBOARD.bat. Credentials: see README "FINAL STEP".
pause
