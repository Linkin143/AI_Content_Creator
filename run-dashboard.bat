@echo off
REM Start only the Streamlit dashboard.
setlocal
set PY=%~dp0.venv\Scripts\python.exe
"%PY%" -m streamlit run app\dashboard\Home.py
endlocal
