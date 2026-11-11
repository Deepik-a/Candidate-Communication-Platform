Write-Host "===================================================" -ForegroundColor Cyan
Write-Host " Starting Candidate Communication Platform" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

$root = $PSScriptRoot

# 1. Dummy Provider
Write-Host "[1/3] Starting Dummy Provider (Port 9000)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root\dummy_provider'; python server.py"

Start-Sleep -Seconds 2

# 2. Backend
Write-Host "[2/3] Starting Backend API (Port 8000)..." -ForegroundColor Yellow
$backendCmd = "Set-Location '$root\backend'; if (Test-Path 'venv\Scripts\Activate.ps1') { . .\venv\Scripts\Activate.ps1 } elseif (Test-Path '.venv312\Scripts\Activate.ps1') { . .\.venv312\Scripts\Activate.ps1 }; python manage.py migrate; python manage.py runserver 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd

Start-Sleep -Seconds 2

# 3. Frontend
Write-Host "[3/3] Starting Frontend (Port 3000)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root\frontend'; npm run dev"

Write-Host "`nAll 3 services have been launched in separate windows!" -ForegroundColor Green
Write-Host "  - Dummy Provider: http://localhost:9000" -ForegroundColor White
Write-Host "  - Backend API:    http://localhost:8000" -ForegroundColor White
Write-Host "  - Frontend UI:    http://localhost:3000" -ForegroundColor White

