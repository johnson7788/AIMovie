# AIMovie Windows one-click startup: backend first, then frontend
$ErrorActionPreference = "Stop"

$RootDir = $PSScriptRoot
$BackendDir = Join-Path $RootDir "backend"
$FrontendDir = Join-Path $RootDir "frontend"
$BackendPort = if ($env:SERVER_PORT) { [int]$env:SERVER_PORT } else { 8666 }
$HealthUrl = "http://127.0.0.1:$BackendPort/health"
$LogDir = Join-Path $RootDir "logs"
$RunStamp = Get-Date -Format "yyyyMMdd-HHmmss"
$BackendLog = Join-Path $LogDir "backend-$RunStamp.log"
$BackendErrLog = Join-Path $LogDir "backend-$RunStamp.err.log"

$BackendProcess = $null
$StartedBackend = $false

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

function Test-BackendReady {
    try {
        $response = Invoke-WebRequest -Uri $HealthUrl -UseBasicParsing -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
            # Verify the response is from our backend (not a random process on the same port)
            $body = $response.Content
            return ($body -match '"status"' -and $body -match '"ok"')
        }
        return $false
    } catch {
        return $false
    }
}

function Clear-Port {
    # Kill any non-backend process occupying the backend port (e.g. IDE port forwarding)
    $connections = Get-NetTCPConnection -LocalPort $BackendPort -State Listen -ErrorAction SilentlyContinue
    foreach ($conn in $connections) {
        $pid = $conn.OwningProcess
        try {
            $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
            if ($proc -and $proc.ProcessName -ne "python") {
                Write-Step "Port $BackendPort is occupied by $($proc.ProcessName) (PID $pid). Killing it..."
                Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
                Start-Sleep -Seconds 1
            }
        } catch {}
    }
}

try {
    foreach ($cmd in @("uv", "node", "npm")) {
        if (-not (Test-CommandExists $cmd)) {
            Write-Host "Error: '$cmd' not found. Please install it and add it to PATH." -ForegroundColor Red
            exit 1
        }
    }
    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

    Write-Step "Syncing backend dependencies (uv sync)..."
    Push-Location $BackendDir
    & uv sync --index-url https://pypi.tuna.tsinghua.edu.cn/simple
    if ($LASTEXITCODE -ne 0) {
        throw "uv sync failed with exit code $LASTEXITCODE"
    }

    Write-Step "Verifying backend runtime deps (ffmpeg for last-frame)..."
    & uv run python -c "from utils.video import _resolve_ffmpeg_exe; p=_resolve_ffmpeg_exe(); print('ffmpeg:', p); import os; assert os.path.isfile(p)"
    if ($LASTEXITCODE -ne 0) {
        throw "Backend dependency verification failed"
    }
    Pop-Location

    Write-Step "Checking port $BackendPort..."
    Clear-Port

    if (Test-BackendReady) {
        Write-Step "Backend is already running on port $BackendPort; reusing it."
    } else {
        Write-Step "Starting backend (backend/main.py)..."
        Write-Step "Backend logs: $BackendLog"
        Write-Step "Backend error logs: $BackendErrLog"
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
        $StartedBackend = $true
        Pop-Location
    }

    Write-Step "Waiting for backend health check: $HealthUrl"
    $maxWaitSeconds = 120
    $waited = 0
    $ready = $false

    while ($waited -lt $maxWaitSeconds) {
        if ($StartedBackend -and $BackendProcess.HasExited) {
            Write-Host "Error: backend process exited early. Last log lines:" -ForegroundColor Red
            if (Test-Path $BackendErrLog) { Get-Content $BackendErrLog -Tail 30 }
            if (Test-Path $BackendLog) { Get-Content $BackendLog -Tail 30 }
            exit 1
        }

        if (Test-BackendReady) {
            $ready = $true
            break
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
    if ($StartedBackend) {
        Stop-Backend
    }
    Pop-Location -ErrorAction SilentlyContinue
}
