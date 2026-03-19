# -*- coding: utf-8 -*-
# NasFusion Startup Script
# Usage: .\start.ps1

Write-Host "========================================"
Write-Host "  NasFusion Startup Script"
Write-Host "========================================"
Write-Host ""

# Get script directory
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Backend configuration
$BackendDir = Join-Path $RootDir "backend"
$VenvActivate = Join-Path $BackendDir "venv\Scripts\Activate.ps1"
$BackendCmd = "python -m app.main"

# Frontend configuration
$FrontendDir = Join-Path $RootDir "frontend"
$FrontendCmd = "npm run dev"

# Check backend virtual environment
if (-not (Test-Path $VenvActivate)) {
    Write-Host "[ERROR] Backend virtual environment not found!" -ForegroundColor Red
    Write-Host "Please run: cd backend && python -m venv venv && .\venv\Scripts\Activate.ps1 && pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

# Check frontend node_modules
if (-not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
    Write-Host "[WARNING] Frontend node_modules not found, installing..." -ForegroundColor Yellow
    Push-Location $FrontendDir
    npm install
    Pop-Location
}

Write-Host "[1/2] Starting backend service..." -ForegroundColor Green
Write-Host "Directory: $BackendDir" -ForegroundColor Gray
Write-Host "Command: $BackendCmd" -ForegroundColor Gray
Write-Host ""

# Start backend in new window
$BackendScript = @"
Set-Location '$BackendDir'
& '$VenvActivate'
Write-Host 'Backend service starting...' -ForegroundColor Green
Write-Host 'API Docs: http://localhost:8000/docs' -ForegroundColor Cyan
Write-Host ''
Invoke-Expression '$BackendCmd'
"@

Start-Process powershell -ArgumentList "-NoExit", "-Command", $BackendScript

# Wait for backend to start
Write-Host "Waiting for backend to start (5 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

Write-Host ""
Write-Host "[2/2] Starting frontend service..." -ForegroundColor Green
Write-Host "Directory: $FrontendDir" -ForegroundColor Gray
Write-Host "Command: $FrontendCmd" -ForegroundColor Gray
Write-Host ""

# Start frontend in new window
$FrontendScript = @"
Set-Location '$FrontendDir'
Write-Host 'Frontend service starting...' -ForegroundColor Green
Write-Host 'Frontend URL: http://localhost:5173' -ForegroundColor Cyan
Write-Host ''
Invoke-Expression '$FrontendCmd'
"@

Start-Process powershell -ArgumentList "-NoExit", "-Command", $FrontendScript

Write-Host ""
Write-Host "========================================"
Write-Host "  Services Started Successfully!"
Write-Host "========================================"
Write-Host ""
Write-Host "Backend API: http://localhost:8000" -ForegroundColor Cyan
Write-Host "API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "Frontend: http://localhost:5173" -ForegroundColor Cyan
Write-Host ""
Write-Host "TIP: Close the PowerShell windows to stop services" -ForegroundColor Yellow
Write-Host ""
