# ===========================================================================
#  AEVRIX Content Intelligence Engine - start the full stack (PowerShell)
#  Opens three windows: FastAPI (OAuth callbacks), Telegram bot, Streamlit.
#  Usage:  powershell -ExecutionPolicy Bypass -File start.ps1
# ===========================================================================
$root = $PSScriptRoot
$py = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $py)) {
    Write-Host "[ERROR] Virtual environment not found at $py" -ForegroundColor Red
    Write-Host "Run scripts\setup.ps1 first."
    exit 1
}

Write-Host "Starting AEVRIX services..." -ForegroundColor Green
Write-Host "  1. FastAPI  http://localhost:8000   (OAuth callbacks + API)"
Write-Host "  2. Telegram bot (long polling)"
Write-Host "  3. Dashboard http://localhost:8501"

Start-Process cmd -ArgumentList '/k', "`"$py`" -m uvicorn app.api.main:app --host 0.0.0.0 --port 8000"
Start-Sleep -Seconds 2
Start-Process cmd -ArgumentList '/k', "`"$py`" -m app.cli run-bot"
Start-Sleep -Seconds 2
Start-Process cmd -ArgumentList '/k', "`"$py`" -m streamlit run app\dashboard\Home.py"

Write-Host ""
Write-Host "All three services launched in separate windows." -ForegroundColor Green
Write-Host "Connect accounts in your browser:" -ForegroundColor Yellow
Write-Host "  X:        http://localhost:8000/auth/x/connect"
Write-Host "  LinkedIn: http://localhost:8000/auth/linkedin/connect"
