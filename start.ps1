# AIMovie Windows one-click startup: backend first, then frontend
$ErrorActionPreference = "Stop"

$RootDir = $PSScriptRoot
$BackendDir = Join-Path $RootDir "backend"
$FrontendDir = Join-Path $RootDir "frontend"
    $BackendPort = if ($env:SERVER_PORT) { [int]$env:SERVER_PORT } else { 8666 }
$HealthUrl = "http://127.0.0.1:$BackendPort/health"
$BackendLog = Join-Path $RootDir "backend.log"
$BackendErrLog = Join-Path $RootDir "backend.err.log"

$BackendProcess = $null

function Write-Step([string]$Message) {
    Write-Host "[start] $Message" -ForegroundColor Green
}

function Stop-Backend {
    if ($null -ne $BackendProcess -and -not $BackendProcess.HasExited) {
        Write-Step "Stopping backend..."
        Stop-Process -Id $BackendProcess.Id -Force -ErrorAction SilentlyContinue
    }
}

function Test-CommandExists([string]$Name) {
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

try {
    foreach ($cmd in @("uv", "node", "npm")) {
        if (-not (Test-CommandExists $cmd)) {
            Write-Host "Error: '$cmd' not found. Please install it and add it to PATH." -ForegroundColor Red
            exit 1
        }
    }

    Write-Step "Syncing backend dependencies (uv sync)..."
    Push-Location $BackendDir
    & uv sync --index-url https://pypi.tuna.tsinghua.edu.cn/simple
    if ($LASTEXITCODE -ne 0) {
        throw "uv sync failed with exit code $LASTEXITCODE"
    }
    Pop-Location

    if (Test-Path $BackendLog) { Remove-Item $BackendLog -Force }
    if (Test-Path $BackendErrLog) { Remove-Item $BackendErrLog -Force }

    Write-Step "Starting backend (backend/main.py)..."
    $env:PYTHONUTF8 = "1"
    Push-Location $BackendDir
    $BackendProcess = Start-Process `
        -FilePath "uv" `
        -ArgumentList @("run", "python", "main.py") `
        -WorkingDirectory $BackendDir `
        -PassThru `
        -NoNewWindow `
        -RedirectStandardOutput $BackendLog `
        -RedirectStandardError $BackendErrLog
    Pop-Location

    Write-Step "Waiting for backend health check: $HealthUrl"
    $maxWaitSeconds = 120
    $waited = 0
    $ready = $false

    while ($waited -lt $maxWaitSeconds) {
        if ($BackendProcess.HasExited) {
            Write-Host "Error: backend process exited early. Last log lines:" -ForegroundColor Red
            if (Test-Path $BackendErrLog) { Get-Content $BackendErrLog -Tail 30 }
            if (Test-Path $BackendLog) { Get-Content $BackendLog -Tail 30 }
            exit 1
        }

        try {
            $response = Invoke-WebRequest -Uri $HealthUrl -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) {
                $ready = $true
                break
            }
        } catch {
            # Backend still starting
        }

        Start-Sleep -Seconds 2
        $waited += 2
    }

    if (-not $ready) {
        Write-Host "Error: backend did not become ready within ${maxWaitSeconds}s." -ForegroundColor Red
        exit 1
    }

    Write-Step "Backend is ready on port $BackendPort"
    Write-Step "API docs: http://127.0.0.1:$BackendPort/docs"

    Write-Step "Starting frontend (vite dev)..."
    Push-Location $FrontendDir

    if (-not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
        Write-Step "First run detected, installing frontend dependencies (npm install)..."
        & npm install
        if ($LASTEXITCODE -ne 0) {
            throw "npm install failed with exit code $LASTEXITCODE"
        }
    }

    $env:VITE_REQUEST_BASE_URL = "http://127.0.0.1:$BackendPort"
    Write-Step "Frontend proxy target: $($env:VITE_REQUEST_BASE_URL)"
    Write-Step "Frontend URL: http://127.0.0.1:36310/aimovie/"
    Write-Step "Press Ctrl+C to stop frontend and backend"

    & npm run dev
}
finally {
    Stop-Backend
    Pop-Location -ErrorAction SilentlyContinue
}
