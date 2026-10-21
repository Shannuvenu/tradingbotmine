@echo off
setlocal
cd /d "%~dp0"
if not exist logs mkdir logs
(where git & git --version) > logs\push_log.txt 2>&1
echo PATH=%PATH% >> logs\push_log.txt
echo ============================================================
echo  Pushing INDIA QUANT to https://github.com/Shannuvenu/tradingbotmine
echo  (.env, secrets\, data_store\, logs\ and .venv\ are excluded by .gitignore)
echo ============================================================
where git >nul 2>nul || (echo NO_GIT>>logs\push_log.txt & echo Git is not installed. Install from https://git-scm.com/download/win and run this again. & pause & exit /b 1)
if not exist ".git" git init -b main
if exist ".env" (
  git check-ignore -q .env || (echo ENV_NOT_IGNORED>>logs\push_log.txt & echo ERROR: .env is not ignored - aborting to protect your keys. & pause & exit /b 1)
)
git config user.name >nul 2>nul || git config user.name "Shannuvenu"
git config user.email >nul 2>nul || git config user.email "Shannuvenu@users.noreply.github.com"
git remote get-url origin >nul 2>nul || git remote add origin https://github.com/Shannuvenu/tradingbotmine.git
git add -A
git status --short | findstr /R /C:"\.env$" /C:"token.json" >nul && (echo ERROR: a secret file is staged - aborting. & pause & exit /b 1)
git commit -q -m "INDIA QUANT: Windows fixes (relative DB path, UTF-8 console, logged scripts)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01JSE3gFPLaXpcfsJgqkWy8A"
git fetch origin >> logs\push_log.txt 2>&1
git rev-parse -q --verify origin/main >nul && git merge --no-edit --allow-unrelated-histories -X ours origin/main
git push -u origin main >> logs\push_log.txt 2>&1
if errorlevel 1 (echo PUSH FAILED - see message above. & pause & exit /b 1)
echo.
echo PUSH OK: https://github.com/Shannuvenu/tradingbotmine
echo PUSH_OK>>logs\push_log.txt
pause
