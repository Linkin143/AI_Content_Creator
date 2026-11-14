@echo off
REM Start only the Telegram bot (long polling).
setlocal
set PY=%~dp0.venv\Scripts\python.exe
"%PY%" -m app.cli run-bot
endlocal
