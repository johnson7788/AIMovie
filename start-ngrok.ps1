# Expose AIMovie frontend (36310) via ngrok so others can access over the internet.
# Prerequisite: run start.bat first so backend + frontend are up.
$ErrorActionPreference = "Stop"

$RootDir = $PSScriptRoot
$NgrokConfig = Join-Path $RootDir "ngrok.yml"
$DefaultNgrokConfig = Join-Path $env:LOCALAPPDATA "ngrok\ngrok.yml"
$FrontendUrl = "http://127.0.0.1:36310/aimovie/"

function Write-Step([string]$Message) {
    Write-Host "[ngrok] $Message" -ForegroundColor Cyan
}

function Test-CommandExists([string]$Name) {
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

if (-not (Test-CommandExists "ngrok")) {
    Write-Host "Error: ngrok not found. Install from https://ngrok.com/download and add to PATH." -ForegroundColor Red
    exit 1
}

if ($env:NGROK_AUTHTOKEN) {
    Write-Step "Configuring ngrok authtoken from NGROK_AUTHTOKEN..."
    & ngrok config add-authtoken $env:NGROK_AUTHTOKEN
    if ($LASTEXITCODE -ne 0) {
        throw "ngrok config add-authtoken failed"
    }
} elseif (-not (Test-Path $DefaultNgrokConfig)) {
    Write-Host @"

Error: ngrok authtoken not configured.
Run once (token from https://dashboard.ngrok.com/get-started/your-authtoken):

  ngrok config add-authtoken <your_authtoken>

Or set environment variable NGROK_AUTHTOKEN before running this script.

"@ -ForegroundColor Red
    exit 1
}

Write-Step "Checking frontend at $FrontendUrl ..."
try {
    $response = Invoke-WebRequest -Uri $FrontendUrl -UseBasicParsing -TimeoutSec 3
    if ($response.StatusCode -ne 200) {
        Write-Host "Warning: frontend returned status $($response.StatusCode)." -ForegroundColor Yellow
    }
} catch {
    Write-Host @"

Error: frontend is not running on port 36310.
Please start the app first:
  1. Double-click start.bat (or run .\start.bat)
  2. Wait until you see the frontend URL in the console
  3. Run this script again in another terminal

"@ -ForegroundColor Red
    exit 1
}

Write-Step "Starting ngrok tunnel (frontend 36310 -> public HTTPS)..."
Write-Step "Share this URL with others (include /aimovie/ path):"
Write-Host "  https://<your-subdomain>.ngrok-free.app/aimovie/" -ForegroundColor Green
Write-Host ""
Write-Step "Press Ctrl+C to stop ngrok (start.bat keeps running separately)."
Write-Host ""

& ngrok start aimovie --config $DefaultNgrokConfig --config $NgrokConfig --log=stdout
