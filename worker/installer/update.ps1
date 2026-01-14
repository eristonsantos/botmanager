# installer/update.ps1
# Script de atualização do RPA Worker

#Requires -RunAsAdministrator

param(
    [string]$InstallPath = "C:\RpaWorker",
    [switch]$SkipBackup = $false
)

$ErrorActionPreference = "Stop"

# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

function Write-Step {
    param([string]$Message)
    Write-Host "`n$Message" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor Green
}

function Write-Error {
    param([string]$Message)
    Write-Host "❌ $Message" -ForegroundColor Red
}

function Write-Warning {
    param([string]$Message)
    Write-Host "⚠️ $Message" -ForegroundColor Yellow
}

# ============================================================================
# BANNER
# ============================================================================

Clear-Host
Write-Host "================================================" -ForegroundColor Yellow
Write-Host "      RPA WORKER - ATUALIZADOR v1.0.0          " -ForegroundColor Yellow
Write-Host "================================================" -ForegroundColor Yellow
Write-Host ""

# ============================================================================
# 1. VERIFICAR INSTALAÇÃO EXISTENTE
# ============================================================================

Write-Step "🔍 Verificando instalação existente..."

if (-not (Test-Path $InstallPath)) {
    Write-Error "RPA Worker não encontrado em: $InstallPath"
    Write-Host "Execute install.ps1 para instalar pela primeira vez."
    exit 1
}

# Verifica serviço
$serviceName = "RpaWorker"
$service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue

if (-not $service) {
    Write-Error "Serviço RpaWorker não encontrado."
    Write-Host "Execute install.ps1 para instalar corretamente."
    exit 1
}

Write-Success "Instalação existente encontrada"

# ============================================================================
# 2. BACKUP AUTOMÁTICO
# ============================================================================

if (-not $SkipBackup) {
    Write-Step "💾 Fazendo backup da instalação atual..."
    
    $backupPath = "$env:TEMP\RpaWorker_Backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    New-Item -ItemType Directory -Path $backupPath -Force | Out-Null
    
    # Backup de arquivos importantes
    $filesToBackup = @(
        ".env",
        "logs",
        "config"
    )
    
    foreach ($item in $filesToBackup) {
        $sourcePath = "$InstallPath\$item"
        if (Test-Path $sourcePath) {
            Copy-Item -Path $sourcePath -Destination $backupPath -Recurse -Force
            Write-Host "   Backup: $item"
        }
    }
    
    Write-Success "Backup criado: $backupPath"
    Write-Host "   (Em caso de problemas, restaure manualmente)"
}

# ============================================================================
# 3. PARAR SERVIÇO E PROCESSOS
# ============================================================================

Write-Step "🛑 Parando serviço e processos..."

$nssmExe = "C:\nssm\nssm.exe"

# Para serviço
if ($service.Status -eq "Running") {
    Write-Host "   Parando serviço RpaWorker..."
    & $nssmExe stop $serviceName
    Start-Sleep -Seconds 3
    
    # Verifica se parou
    $service.Refresh()
    if ($service.Status -ne "Stopped") {
        Write-Warning "Serviço não parou gracefully. Forçando..."
        Stop-Service -Name $serviceName -Force
        Start-Sleep -Seconds 2
    }
}

# Fecha UI se estiver aberta
$uiProcess = Get-Process -Name "rpa-worker-ui" -ErrorAction SilentlyContinue
if ($uiProcess) {
    Write-Host "   Fechando UI..."
    $uiProcess | Stop-Process -Force
    Start-Sleep -Seconds 1
}

Write-Success "Serviço e processos parados"

# ============================================================================
# 4. ATUALIZAR ARQUIVOS PYTHON
# ============================================================================

Write-Step "📦 Atualizando arquivos do Worker..."

$workerFiles = @(
    "worker\main.py",
    "worker\manager.py",
    "worker\automation_runner.py",
    "worker\config.py",
    "worker\requirements.txt"
)

foreach ($file in $workerFiles) {
    if (Test-Path $file) {
        Copy-Item -Path $file -Destination $InstallPath -Force
        Write-Host "   Atualizado: $(Split-Path $file -Leaf)"
    } else {
        Write-Warning "Arquivo não encontrado: $file"
    }
}

Write-Success "Arquivos Python atualizados"

# ============================================================================
# 5. ATUALIZAR DEPENDÊNCIAS
# ============================================================================

Write-Step "🐍 Atualizando dependências Python..."

Push-Location $InstallPath

# Atualiza pip
& python -m pip install --upgrade pip --quiet

# Atualiza dependências
& pip install -r requirements.txt --upgrade --quiet

Pop-Location

Write-Success "Dependências atualizadas"

# ============================================================================
# 6. ATUALIZAR UI (SE DISPONÍVEL)
# ============================================================================

Write-Step "🖥️ Verificando atualização da UI..."

$newUIExe = "ui\src-tauri\target\release\rpa-worker-ui.exe"

if (Test-Path $newUIExe) {
    Write-Host "   Nova versão da UI encontrada. Atualizando..."
    
    # Remove executável antigo
    $oldUIExe = "$InstallPath\RpaWorkerUI.exe"
    if (Test-Path $oldUIExe) {
        Remove-Item -Path $oldUIExe -Force
    }
    
    # Copia nova versão
    Copy-Item -Path $newUIExe -Destination "$InstallPath\RpaWorkerUI.exe" -Force
    
    Write-Success "UI atualizada"
} else {
    Write-Host "   Nova versão da UI não encontrada (pulando)"
}

# ============================================================================
# 7. PRESERVAR CONFIGURAÇÕES
# ============================================================================

Write-Step "⚙️ Verificando configurações..."

$envPath = "$InstallPath\.env"

if (Test-Path $envPath) {
    Write-Host "   Configurações preservadas (.env existe)"
} else {
    Write-Warning "Arquivo .env não encontrado!"
    
    if (Test-Path "$InstallPath\.env.example") {
        Copy-Item -Path "$InstallPath\.env.example" -Destination $envPath -Force
        Write-Host "   Criado .env a partir do template"
        Write-Warning "   IMPORTANTE: Configure o .env antes de iniciar o serviço!"
    }
}

Write-Success "Configurações verificadas"

# ============================================================================
# 8. REINICIAR SERVIÇO
# ============================================================================

Write-Step "🔄 Reiniciando serviço..."

& $nssmExe start $serviceName
Start-Sleep -Seconds 3

# Verifica se iniciou
$service = Get-Service -Name $serviceName
$service.Refresh()

if ($service.Status -eq "Running") {
    Write-Success "Serviço reiniciado com sucesso"
} else {
    Write-Error "Serviço não iniciou!"
    Write-Host "   Verifique os logs em: $InstallPath\logs\"
    Write-Host "   Tente iniciar manualmente com: nssm start RpaWorker"
    exit 1
}

# ============================================================================
# 9. TESTAR API
# ============================================================================

Write-Step "🧪 Testando API..."

Start-Sleep -Seconds 2

try {
    $response = Invoke-WebRequest -Uri "http://localhost:8765/" -TimeoutSec 5 -UseBasicParsing
    
    if ($response.StatusCode -eq 200) {
        Write-Success "API respondendo corretamente"
    } else {
        Write-Warning "API respondeu com status: $($response.StatusCode)"
    }
} catch {
    Write-Warning "API não respondeu. Verifique os logs."
}

# ============================================================================
# 10. VERIFICAR VERSÃO
# ============================================================================

Write-Step "📋 Verificando versão..."

try {
    $statusResponse = Invoke-RestMethod -Uri "http://localhost:8765/status" -TimeoutSec 5
    
    Write-Host "   Worker: $($statusResponse.worker_name)"
    Write-Host "   Versão: $($statusResponse.version)"
    Write-Host "   Status: $(if ($statusResponse.running) { 'Rodando ✅' } else { 'Parado ⏹️' })"
    
} catch {
    Write-Warning "Não foi possível obter versão da API"
}

# ============================================================================
# RESUMO FINAL
# ============================================================================

Write-Host "`n================================================" -ForegroundColor Green
Write-Host "      ATUALIZAÇÃO CONCLUÍDA COM SUCESSO!        " -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Host "✅ Arquivos Python atualizados" -ForegroundColor Cyan
Write-Host "✅ Dependências atualizadas" -ForegroundColor Cyan
Write-Host "✅ Serviço reiniciado" -ForegroundColor Cyan

if (Test-Path $newUIExe) {
    Write-Host "✅ UI atualizada" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "📍 Instalação: $InstallPath" -ForegroundColor Cyan
Write-Host "🔧 Serviço: RpaWorker (rodando)" -ForegroundColor Cyan
Write-Host "🌐 API: http://localhost:8765" -ForegroundColor Cyan
Write-Host ""

if (-not $SkipBackup) {
    Write-Host "💾 Backup disponível em: $backupPath" -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "⚠️ IMPORTANTE:" -ForegroundColor Yellow
Write-Host "   Se você atualizou o .env, reinicie o serviço:" -ForegroundColor Yellow
Write-Host "   nssm restart RpaWorker" -ForegroundColor Yellow
Write-Host ""