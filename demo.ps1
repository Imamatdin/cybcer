# Cerebras Red Team Simulator - Demo Script
# Run from project root: .\demo.ps1

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║     CEREBRAS RED TEAM SIMULATOR - LIVE DEMONSTRATION         ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Check for API key
if (-not $env:CEREBRAS_API_KEY) {
    # Try to load from .env file
    if (Test-Path ".env") {
        Get-Content ".env" | ForEach-Object {
            if ($_ -match "^([^#=]+)=(.+)$") {
                $key = $matches[1].Trim()
                $value = $matches[2].Trim().Trim('"').Trim("'")
                [Environment]::SetEnvironmentVariable($key, $value)
            }
        }
    }
    
    if (-not $env:CEREBRAS_API_KEY) {
        Write-Host "Error: CEREBRAS_API_KEY not set" -ForegroundColor Red
        Write-Host "Set it with: `$env:CEREBRAS_API_KEY = 'your-key'" -ForegroundColor Yellow
        exit 1
    }
}

Write-Host "[1/3] Starting vulnerable target..." -ForegroundColor Green

# Start vulnerable app in background
$appJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    Set-Location vulnerable_app
    python app.py 2>&1
}

Start-Sleep -Seconds 3

# Verify app is running
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:5000" -UseBasicParsing -TimeoutSec 5
    Write-Host "Target running at http://127.0.0.1:5000" -ForegroundColor Green
} catch {
    Write-Host "Failed to start vulnerable app" -ForegroundColor Red
    Stop-Job $appJob
    Remove-Job $appJob
    exit 1
}

Write-Host ""
Write-Host "[2/3] Launching autonomous attack..." -ForegroundColor Green
Write-Host ""

# Run attack
python main.py --target http://127.0.0.1:5000 --max-steps 15

Write-Host ""
Write-Host "[3/3] Cleaning up..." -ForegroundColor Green

# Cleanup
Stop-Job $appJob -ErrorAction SilentlyContinue
Remove-Job $appJob -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "Demo complete!" -ForegroundColor Cyan
