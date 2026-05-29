# AI Medical Coder — Windows Setup Script (PowerShell)
# Run from the project root: .\setup.ps1

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $ProjectRoot "backend"

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  AI Medical Coder — Setup" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check Python version
Write-Host "[1/8] Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  Found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Python not found. Install Python 3.11+ from https://python.org" -ForegroundColor Red
    exit 1
}

# 2. Create virtual environment
Write-Host "[2/8] Creating virtual environment..." -ForegroundColor Yellow
Set-Location $BackendDir
if (-not (Test-Path "venv")) {
    python -m venv venv
    Write-Host "  Virtual environment created" -ForegroundColor Green
} else {
    Write-Host "  Virtual environment already exists" -ForegroundColor Green
}

# 3. Activate venv and install dependencies
Write-Host "[3/8] Installing Python dependencies..." -ForegroundColor Yellow
& ".\venv\Scripts\pip.exe" install --upgrade pip --quiet
& ".\venv\Scripts\pip.exe" install -r requirements.txt
Write-Host "  Dependencies installed" -ForegroundColor Green

# 4. Install scispaCy model
Write-Host "[4/8] Installing scispaCy clinical NLP model..." -ForegroundColor Yellow
Write-Host "  (This downloads ~600MB — may take a few minutes)" -ForegroundColor Gray
try {
    & ".\venv\Scripts\pip.exe" install "https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_lg-0.5.4.tar.gz"
    Write-Host "  scispaCy model installed" -ForegroundColor Green
} catch {
    Write-Host "  WARNING: scispaCy model install failed. Running with fallback NLP." -ForegroundColor Yellow
    Write-Host "  You can install later: pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_lg-0.5.4.tar.gz" -ForegroundColor Gray
}

# 5. Copy .env file
Write-Host "[5/8] Setting up environment configuration..." -ForegroundColor Yellow
$EnvExample = Join-Path $ProjectRoot ".env.example"
$EnvFile = Join-Path $BackendDir ".env"
if (-not (Test-Path $EnvFile)) {
    Copy-Item $EnvExample $EnvFile
    Write-Host "  Created .env file — please review and update settings" -ForegroundColor Green
} else {
    Write-Host "  .env already exists — skipping" -ForegroundColor Green
}

# 6. Build knowledge base
Write-Host "[6/8] Building knowledge base (downloading ICD-10, HCPCS codes)..." -ForegroundColor Yellow
Write-Host "  (This may take a few minutes to download and index)" -ForegroundColor Gray
Set-Location $BackendDir
try {
    & ".\venv\Scripts\python.exe" knowledge_base/scripts/build_knowledge_base.py
    Write-Host "  Knowledge base built" -ForegroundColor Green
} catch {
    Write-Host "  WARNING: Knowledge base build had issues. Check the output above." -ForegroundColor Yellow
}

# 7. Check Ollama
Write-Host "[7/8] Checking Ollama (local LLM server)..." -ForegroundColor Yellow
try {
    $ollamaVersion = ollama --version 2>&1
    Write-Host "  Found: $ollamaVersion" -ForegroundColor Green
    Write-Host "  Pulling llama3.1:8b model (this downloads ~5GB)..." -ForegroundColor Gray
    Write-Host "  You can skip this and use Claude API instead (set LLM_PROVIDER=anthropic in .env)" -ForegroundColor Gray
    $pullChoice = Read-Host "  Pull llama3.1:8b now? [y/N]"
    if ($pullChoice -eq "y" -or $pullChoice -eq "Y") {
        ollama pull llama3.1:8b
        Write-Host "  Model pulled" -ForegroundColor Green
    }
} catch {
    Write-Host "  Ollama not found. Install from https://ollama.com" -ForegroundColor Yellow
    Write-Host "  OR: Set LLM_PROVIDER=anthropic in backend/.env and add your API key" -ForegroundColor Gray
}

# 8. Run tests
Write-Host "[8/8] Running tests..." -ForegroundColor Yellow
try {
    & ".\venv\Scripts\pytest.exe" tests/test_nlp.py tests/test_coding.py -v --tb=short
    Write-Host "  Tests passed" -ForegroundColor Green
} catch {
    Write-Host "  Some tests failed — check output above" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  Setup Complete!" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To start the AI Medical Coder API:" -ForegroundColor White
Write-Host "  cd backend" -ForegroundColor Gray
Write-Host "  .\venv\Scripts\uvicorn.exe app.main:app --reload --host 0.0.0.0 --port 8000" -ForegroundColor Gray
Write-Host ""
Write-Host "API will be available at:" -ForegroundColor White
Write-Host "  http://localhost:8000/docs     (Interactive API documentation)" -ForegroundColor Gray
Write-Host "  http://localhost:8000/health   (Health check)" -ForegroundColor Gray
Write-Host "  http://localhost:8000/         (Root endpoint)" -ForegroundColor Gray
Write-Host ""
Write-Host "Quick test:" -ForegroundColor White
Write-Host '  curl -X POST "http://localhost:8000/api/v1/coding/code" \' -ForegroundColor Gray
Write-Host '    -H "Content-Type: application/json" \' -ForegroundColor Gray
Write-Host '    -d "{\"text\": \"Patient with type 2 diabetes and hypertension.\", \"specialty\": \"general\"}"' -ForegroundColor Gray
Write-Host ""
