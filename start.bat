@echo off
REM ===========================================================================
REM  AEVRIX Content Intelligence Engine - start the full stack (Windows cmd)
REM  Opens three windows: FastAPI (OAuth callbacks), Telegram bot, Streamlit.
REM  Double-click this file, or run `start.bat` from a terminal.
REM ===========================================================================
setlocal
set ROOT=%~dp0
set PY=%ROOT%.venv\Scripts\python.exe

if not exist "%PY%" (
    echo [ERROR] Virtual environment not found at %PY%
    echo Run scripts\setup.ps1 first.
    pause
    exit /b 1
)

echo Starting AEVRIX services...
echo   1. FastAPI  http://localhost:8000   (OAuth callbacks + API)
echo   2. Telegram bot (long polling)
echo   3. Dashboard http://localhost:8501

start "AEVRIX API" cmd /k ""%PY%" -m uvicorn app.api.main:app --host 0.0.0.0 --port 8000"
timeout /t 2 >nul
start "AEVRIX Telegram Bot" cmd /k ""%PY%" -m app.cli run-bot"
timeout /t 2 >nul
start "AEVRIX Dashboard" cmd /k ""%PY%" -m streamlit run app\dashboard\Home.py"

echo.
echo All three services launched in separate windows.
echo Connect accounts in your browser:
echo   X:        http://localhost:8000/auth/x/connect
echo   LinkedIn: http://localhost:8000/auth/linkedin/connect
echo.
endlocal
