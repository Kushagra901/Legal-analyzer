<#
.SYNOPSIS
    Launches the full Legal Analyzer local development environment in separate PowerShell windows.

.DESCRIPTION
    1. Checks if Ollama is running; starts 'ollama serve' in a new window if not.
    2. Opens a new PowerShell window, activates backend .venv, and runs uvicorn.
    3. Opens a new PowerShell window, enters frontend, and runs npm run dev.
    4. Waits for services to initialize and displays a health check summary.
#>

$ErrorActionPreference = "Continue"

$RootDir = $PSScriptRoot
if (-not $RootDir) {
    $RootDir = (Get-Location).Path
}

$BackendDir  = Join-Path $RootDir "backend"
$FrontendDir = Join-Path $RootDir "frontend"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "       Launching Legal Analyzer Local Development           " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Project Root: $RootDir" -ForegroundColor Gray
Write-Host ""

# -------------------------------------------------------------
# 1. Ollama Check & Launch
# -------------------------------------------------------------
Write-Host "[1/3] Checking Ollama service..." -ForegroundColor Yellow

function Test-OllamaRunning {
    # Check using curl.exe if available (fast and handles IPv4/IPv6 automatically)
    try {
        $curlOutput = & curl.exe -s --connect-timeout 2 http://localhost:11434 2>$null
        if ($curlOutput -match "Ollama is running") { return $true }
    } catch {}

    # Fallback to Invoke-WebRequest on 127.0.0.1
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:11434" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($resp.StatusCode -eq 200) { return $true }
    } catch {}

    return $false
}

$ollamaRunning = Test-OllamaRunning

if ($ollamaRunning) {
    Write-Host "      Ollama is already running on http://localhost:11434." -ForegroundColor Green
} else {
    Write-Host "      Ollama not detected. Starting 'ollama serve' in a new PowerShell window..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "Write-Host 'Starting Ollama Service (ollama serve)...' -ForegroundColor Cyan; ollama serve"
}

# -------------------------------------------------------------
# 2. FastAPI Backend Launch
# -------------------------------------------------------------
Write-Host "[2/3] Starting FastAPI backend..." -ForegroundColor Yellow

if (-not (Test-Path $BackendDir)) {
    Write-Host "      [ERROR] Backend directory not found at $BackendDir!" -ForegroundColor Red
} else {
    $backendCmd = "Set-Location '$BackendDir'; " +
                  "if (Test-Path '.\.venv\Scripts\Activate.ps1') { " +
                  "    Write-Host 'Activating Python virtual environment (.venv)...' -ForegroundColor Green; " +
                  "    .\.venv\Scripts\Activate.ps1 " +
                  "} else { " +
                  "    Write-Host '[WARN] .venv not found, using default python.' -ForegroundColor Yellow " +
                  "}; " +
                  "Write-Host 'Starting Uvicorn dev server on http://localhost:8000...' -ForegroundColor Cyan; " +
                  "uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

    Start-Process powershell -ArgumentList "-ExecutionPolicy", "Bypass", "-NoExit", "-Command", $backendCmd
    Write-Host "      FastAPI backend launched in a new window (port 8000)." -ForegroundColor Green
}

# -------------------------------------------------------------
# 3. Next.js Frontend Launch
# -------------------------------------------------------------
Write-Host "[3/3] Starting Next.js frontend..." -ForegroundColor Yellow

if (-not (Test-Path $FrontendDir)) {
    Write-Host "      [ERROR] Frontend directory not found at $FrontendDir!" -ForegroundColor Red
} else {
    $frontendCmd = "Set-Location '$FrontendDir'; " +
                   "Write-Host 'Starting Next.js frontend on http://localhost:3000...' -ForegroundColor Cyan; " +
                   "npm run dev"

    Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd
    Write-Host "      Next.js frontend launched in a new window (port 3000)." -ForegroundColor Green
}

# -------------------------------------------------------------
# 4. Service Health Checks & Summary
# -------------------------------------------------------------
Write-Host ""
Write-Host "Waiting for services to initialize..." -ForegroundColor Cyan

function Test-HttpEndpoint {
    param(
        [string]$Url,
        [int]$TimeoutSec = 1
    )
    try {
        $code = & curl.exe -s -o /dev/null -w "%{http_code}" --connect-timeout $TimeoutSec $Url 2>$null
        if ($code -match "^[23]\d\d$") { return $true }
    } catch {}

    try {
        $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $TimeoutSec -ErrorAction Stop
        if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 400) { return $true }
    } catch {}

    return $false
}

$maxWaitSec = 20
$elapsed = 0
$backendHealthy = $false
$frontendHealthy = $false
$ollamaHealthy = $false

while ($elapsed -lt $maxWaitSec) {
    Start-Sleep -Seconds 2
    $elapsed += 2

    if (-not $ollamaHealthy) {
        $ollamaHealthy = Test-OllamaRunning
    }
    if (-not $backendHealthy) {
        $backendHealthy = (Test-HttpEndpoint "http://127.0.0.1:8000/health" 1) -or (Test-HttpEndpoint "http://localhost:8000/health" 1)
    }
    if (-not $frontendHealthy) {
        $frontendHealthy = (Test-HttpEndpoint "http://localhost:3000" 1) -or (Test-HttpEndpoint "http://127.0.0.1:3000" 1)
    }

    $readyCount = 0
    if ($ollamaHealthy) { $readyCount++ }
    if ($backendHealthy) { $readyCount++ }
    if ($frontendHealthy) { $readyCount++ }

    Write-Host "  ... waiting for services: $readyCount/3 ready ($elapsed/${maxWaitSec}s)" -ForegroundColor Gray

    if ($ollamaHealthy -and $backendHealthy -and $frontendHealthy) {
        break
    }
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "               Service Health Status Summary                " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

function Format-StatusLine {
    param(
        [string]$Name,
        [string]$Url,
        [bool]$Healthy,
        [string]$ExtraInfo = ""
    )
    $statusText = if ($Healthy) { "[HEALTHY / RUNNING]" } else { "[NOT RESPONDING]   " }
    $color = if ($Healthy) { "Green" } else { "Red" }

    Write-Host "  $($Name.PadRight(10)) : $Url" -NoNewline
    if ($ExtraInfo) {
        Write-Host " ($ExtraInfo)" -ForegroundColor Gray -NoNewline
    }
    Write-Host ""
    Write-Host "               Status: " -NoNewline
    Write-Host "$statusText" -ForegroundColor $color
}

Format-StatusLine "Ollama"   "http://localhost:11434"      $ollamaHealthy
Format-StatusLine "Backend"  "http://localhost:8000"       $backendHealthy  "API Docs: http://localhost:8000/docs"
Format-StatusLine "Frontend" "http://localhost:3000"       $frontendHealthy

# Optional check for self-hosted n8n container
try {
    $n8nHealthy = (Test-HttpEndpoint "http://127.0.0.1:5678" 1) -or (Test-HttpEndpoint "http://localhost:5678" 1)
    if ($n8nHealthy) {
        Format-StatusLine "n8n" "http://localhost:5678" $true "Workflow Orchestration"
    }
} catch {}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Ready for development! Close any launched window to stop." -ForegroundColor Green
Write-Host ""
