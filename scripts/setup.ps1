# AEVRIX Content Intelligence Engine - Windows setup script
# Usage:  powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
#
# Creates a virtual environment, installs dependencies, prepares .env and
# initializes the database. Uses `uv` if available, otherwise falls back to pip.

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "==> AEVRIX setup starting in $root" -ForegroundColor Green

# 1. Choose installer
$useUv = $false
if (Get-Command uv -ErrorAction SilentlyContinue) { $useUv = $true }

# 2. Create virtual environment
if (-not (Test-Path ".venv")) {
    Write-Host "==> Creating virtual environment (.venv)" -ForegroundColor Cyan
    if ($useUv) { uv venv } else { python -m venv .venv }
}

$py = ".\.venv\Scripts\python.exe"

# 3. Install dependencies
Write-Host "==> Installing dependencies" -ForegroundColor Cyan
if ($useUv) {
    uv pip install -e ".[dev]"
    Write-Host "    (optional providers) uv pip install langchain-ollama langchain-openai langchain-google-genai langchain-groq"
} else {
    & $py -m pip install --upgrade pip
    & $py -m pip install -e ".[dev]"
}

# 4. Prepare .env
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "==> Created .env from .env.example" -ForegroundColor Cyan
    $key = & $py -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    (Get-Content ".env") -replace "^APP_ENCRYPTION_KEY=.*", "APP_ENCRYPTION_KEY=$key" | Set-Content ".env"
    Write-Host "    Generated APP_ENCRYPTION_KEY and wrote it to .env" -ForegroundColor Cyan
}

# 5. Initialize database
Write-Host "==> Initializing database" -ForegroundColor Cyan
& $py -m app.cli init-db

Write-Host ""
Write-Host "==> Setup complete." -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Edit .env (choose an LLM provider; add Telegram/X/LinkedIn if desired)."
Write-Host "  2. Test provider:   $py -m app.cli test-provider"
Write-Host "  3. Run research:    $py -m app.cli research"
Write-Host "  4. API:             uvicorn app.api.main:app --reload"
Write-Host "  5. Dashboard:       streamlit run app/dashboard/Home.py"
