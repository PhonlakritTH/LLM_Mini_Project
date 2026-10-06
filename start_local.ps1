# ============================================================
# start_local.ps1 - Run all backend services on localhost
# ============================================================
# Usage: .\start_local.ps1
#   Press Ctrl+C to stop all services
# ============================================================

$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path

# Find Python
$PYTHON = if (Test-Path "$ROOT\.venv\Scripts\python.exe") {
    "$ROOT\.venv\Scripts\python.exe"
} else {
    "python"
}

Write-Host "=== PC Spec Builder - Local Dev Startup ===" -ForegroundColor Cyan
Write-Host "Root: $ROOT" -ForegroundColor Gray
Write-Host "Python: $PYTHON" -ForegroundColor Gray
Write-Host ""

# Service definitions: port, folder, app module
$services = @(
    @{ port=8200; dir="04_external_data_services";           app="app.main:app" }
    @{ port=8100; dir="03_pc_build_ai_agent";                app="app.main:app" }
    @{ port=8300; dir="05_data_integration";                 app="app.main:app" }
    @{ port=8400; dir="06_compatibility_knowledge_services"; app="app.main:app" }
    @{ port=8500; dir="07_decision_llm_engine";              app="app.main:app" }
    @{ port=8600; dir="08_recommendation_feedback";          app="app.main:app" }
    @{ port=8000; dir="02_api_backend";                      app="app.main:app" }
)

$jobs = @()

foreach ($svc in $services) {
    $svcDir = Join-Path $ROOT $svc.dir
    $port   = $svc.port
    $appMod = $svc.app
    $label  = $svc.dir

    Write-Host "Starting [$label] on port $port ..." -ForegroundColor Yellow

    $jobs += Start-Job -Name $label -ScriptBlock {
        param($python, $dir, $port, $app)
        $env:PYTHONUTF8 = "1"
        $env:PYTHONIOENCODING = "utf-8"
        Set-Location $dir
        & $python -m uvicorn $app --host 0.0.0.0 --port $port --log-level info 2>&1
    } -ArgumentList $PYTHON, $svcDir, $port, $appMod
}

Write-Host ""
Write-Host "All services started. Waiting 5s for startup..." -ForegroundColor Green
Start-Sleep -Seconds 5

# Health checks
Write-Host ""
Write-Host "=== Health Checks ===" -ForegroundColor Cyan
$ports = @(8200, 8100, 8300, 8400, 8500, 8600, 8000)
foreach ($p in $ports) {
    try {
        $resp = Invoke-WebRequest -Uri "http://localhost:$p/health" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        Write-Host "  :$p  OK  - $($resp.Content)" -ForegroundColor Green
    } catch {
        Write-Host "  :$p  NOT READY - $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "=== Swagger UI Links ===" -ForegroundColor Cyan
Write-Host "  External Data    : http://localhost:8200/docs" -ForegroundColor White
Write-Host "  AI Agent         : http://localhost:8100/docs" -ForegroundColor White
Write-Host "  Data Integration : http://localhost:8300/docs" -ForegroundColor White
Write-Host "  Knowledge Svc    : http://localhost:8400/docs" -ForegroundColor White
Write-Host "  Decision LLM     : http://localhost:8500/docs" -ForegroundColor White
Write-Host "  Recommendation   : http://localhost:8600/docs" -ForegroundColor White
Write-Host "  API Gateway      : http://localhost:8000/docs  <-- Main" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop all services..." -ForegroundColor Gray

# Stream logs until Ctrl+C
try {
    while ($true) {
        foreach ($job in $jobs) {
            $output = Receive-Job -Job $job -ErrorAction SilentlyContinue
            if ($output) {
                Write-Host "[$($job.Name)] $output" -ForegroundColor DarkGray
            }
        }
        Start-Sleep -Seconds 1
    }
} finally {
    Write-Host ""
    Write-Host "Stopping all services..." -ForegroundColor Yellow
    $jobs | Stop-Job
    $jobs | Remove-Job
    Write-Host "Done." -ForegroundColor Green
}
