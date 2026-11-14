@echo off
REM Start only the FastAPI server (needed for X/LinkedIn OAuth callbacks).
setlocal
set PY=%~dp0.venv\Scripts\python.exe
"%PY%" -m uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload
endlocal
