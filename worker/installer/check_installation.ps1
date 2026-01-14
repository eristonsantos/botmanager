# installer/check_installation.ps1
# Script para verificar saúde da instalação

param(
    [string]$InstallPath = "C:\RpaWorker"
)

# ============================================================================
# FUNÇÕES
# ============================================================================

function Write-Check {
    param([string]$Item, [bool]$Status)
    $icon = if ($Status) { "✅" } else { "❌" }
    $color = if ($Status) { "Green" } else { "Red" }
    Write-Host "$icon $Item" -ForegroundColor $color
}

# ============================================================================
# VERIFICAÇÕES
# ============================================================================

Clear-Host
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "   RPA WORKER - VERIFICAÇÃO DE INSTALAÇÃO      " -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Diretório de instalação
Write-Host "📁 Diretório de Instalação:" -ForegroundColor Yellow
$dirExists = Test-Path $InstallPath
Write-Check "Diretório existe: $InstallPath" $dirExists

if ($dirExists) {
    $requiredDirs = @("logs", "config", "automations")
    foreach ($dir in $requiredDirs) {
        $exists = Test-Path "$InstallPath\$dir"
        Write-Check "  ├─ $dir\" $exists
    }
}

Write-Host ""

# 2. Arquivos Python
Write-Host "🐍 Arquivos Python:" -ForegroundColor Yellow
$pythonFiles = @("main.py", "manager.py", "automation_runner.py", "config.py", "requirements.txt")
foreach ($file in $pythonFiles) {
    $exists = Test-Path "$InstallPath\$file"
    Write-Check "  $file" $exists
}

Write-Host ""

# 3. Configuração
Write-Host "⚙️ Configuração:" -ForegroundColor Yellow
$envExists = Test-Path "$InstallPath\.env"
Write-Check ".env configurado" $envExists

if ($envExists) {
    $envContent = Get-Content "$InstallPath\.env" -Raw
    Write-Check "  ├─ ORCHESTRATOR_URL definida" ($envContent -match "ORCHESTRATOR_URL=.+")
    Write-Check "  ├─ API_KEY definida" ($envContent -match "API_KEY=.+")
    Write-Check "  └─ TENANT_ID definido" ($envContent -match "TENANT_ID=.+")
}

Write-Host ""

# 4. Serviço Windows
Write-Host "🔧 Serviço Windows:" -ForegroundColor Yellow
$service = Get-Service -Name "RpaWorker" -ErrorAction SilentlyContinue
$serviceExists = $null -ne $service

Write-Check "Serviço instalado" $serviceExists

if ($serviceExists) {
    Write-Check "  ├─ Status: $($service.Status)" ($service.Status -eq "Running")
    Write-Check "  └─ Startup: $($service.StartType)" ($service.StartType -eq "Automatic")
}

Write-Host ""

# 5. API Local
Write-Host "🌐 API Local:" -ForegroundColor Yellow

try {
    $response = Invoke-WebRequest -Uri "http://localhost:8765/" -TimeoutSec 3 -UseBasicParsing
    Write-Check "API respondendo (porta 8765)" ($response.StatusCode -eq 200)
    
    # Tenta obter status
    try {
        $status = Invoke-RestMethod -Uri "http://localhost:8765/status" -TimeoutSec 3
        Write-Check "  ├─ Worker: $(