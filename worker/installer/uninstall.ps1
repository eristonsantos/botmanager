# installer/uninstall.ps1
# Script de desinstalação do RPA Worker

#Requires -RunAsAdministrator

param(
    [string]$InstallPath = "C:\RpaWorker",
    [switch]$KeepLogs = $false,
    [switch]$KeepConfig = $false
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
Write-Host "================================================" -ForegroundColor Red
Write-Host "     RPA WORKER - DESINSTALADOR v1.0.0         " -ForegroundColor Red
Write-Host "================================================" -ForegroundColor Red
Write-Host ""

# Confirmação
Write-Warning "Esta ação irá remover completamente o RPA Worker do sistema."
$confirm = Read-Host "Deseja continuar? (S/N)"
if ($confirm -ne "S" -and $confirm -ne "s") {
    Write-Host "Desinstalação cancelada."
    exit 0
}

# ============================================================================
# 1. PARAR E REMOVER SERVIÇO
# ============================================================================

Write-Step "🛑 Parando e removendo serviço..."

$serviceName = "RpaWorker"
$nssmExe = "C:\nssm\nssm.exe"

$service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue

if ($service) {
    # Para o serviço
    if ($service.Status -eq "Running") {
        Write-Host "   Parando serviço..."
        & $nssmExe stop $serviceName
        Start-Sleep -Seconds 2
    }
    
    # Remove o serviço
    Write-Host "   Removendo serviço..."
    & $nssmExe remove $serviceName confirm
    
    Write-Success "Serviço removido"
} else {
    Write-Host "   Serviço não encontrado (já removido)"
}

# ============================================================================
# 2. FECHAR PROCESSOS DO WORKER
# ============================================================================

Write-Step "🔄 Encerrando processos do Worker..."

# Fecha UI se estiver aberta
$uiProcess = Get-Process -Name "rpa-worker-ui" -ErrorAction SilentlyContinue
if ($uiProcess) {
    Write-Host "   Fechando UI..."
    $uiProcess | Stop-Process -Force
}

# Fecha processos Python do worker
$workerProcesses = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $_.Path -like "*RpaWorker*"
}

if ($workerProcesses) {
    Write-Host "   Encerrando processos Python..."
    $workerProcesses | Stop-Process -Force
}

Write-Success "Processos encerrados"

# ============================================================================
# 3. REMOVER ATALHOS
# ============================================================================

Write-Step "🔗 Removendo atalhos..."

$shortcuts = @(
    "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\RPA Worker.lnk",
    "$env:PUBLIC\Desktop\RPA Worker.lnk"
)

foreach ($shortcut in $shortcuts) {
    if (Test-Path $shortcut) {
        Remove-Item -Path $shortcut -Force
        Write-Host "   Removido: $shortcut"
    }
}

Write-Success "Atalhos removidos"

# ============================================================================
# 4. REMOVER REGRA DE FIREWALL
# ============================================================================

Write-Step "🔥 Removendo regra de firewall..."

$firewallRule = Get-NetFirewallRule -DisplayName "RPA Worker API" -ErrorAction SilentlyContinue

if ($firewallRule) {
    Remove-NetFirewallRule -DisplayName "RPA Worker API"
    Write-Success "Regra de firewall removida"
} else {
    Write-Host "   Regra de firewall não encontrada"
}

# ============================================================================
# 5. BACKUP DE DADOS (SE SOLICITADO)
# ============================================================================

if ($KeepLogs -or $KeepConfig) {
    Write-Step "💾 Fazendo backup..."
    
    $backupPath = "$env:USERPROFILE\Desktop\RpaWorker_Backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    New-Item -ItemType Directory -Path $backupPath -Force | Out-Null
    
    if ($KeepLogs -and (Test-Path "$InstallPath\logs")) {
        Copy-Item -Path "$InstallPath\logs" -Destination "$backupPath\logs" -Recurse -Force
        Write-Host "   Logs salvos em: $backupPath\logs"
    }
    
    if ($KeepConfig -and (Test-Path "$InstallPath\.env")) {
        Copy-Item -Path "$InstallPath\.env" -Destination "$backupPath\.env" -Force
        Copy-Item -Path "$InstallPath\config" -Destination "$backupPath\config" -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "   Configurações salvas em: $backupPath"
    }
    
    Write-Success "Backup concluído: $backupPath"
}

# ============================================================================
# 6. REMOVER DIRETÓRIO DE INSTALAÇÃO
# ============================================================================

Write-Step "📁 Removendo diretório de instalação..."

if (Test-Path $InstallPath) {
    try {
        Remove-Item -Path $InstallPath -Recurse -Force -ErrorAction Stop
        Write-Success "Diretório removido: $InstallPath"
    } catch {
        Write-Warning "Não foi possível remover completamente: $InstallPath"
        Write-Host "   Alguns arquivos podem estar em uso. Tente remover manualmente."
    }
} else {
    Write-Host "   Diretório não encontrado (já removido)"
}

# ============================================================================
# 7. REMOVER CONFIGURAÇÕES DO USUÁRIO
# ============================================================================

Write-Step "⚙️ Removendo configurações do usuário..."

$userConfigPath = "$env:APPDATA\RpaWorker"

if (Test-Path $userConfigPath) {
    Remove-Item -Path $userConfigPath -Recurse -Force
    Write-Host "   Removido: $userConfigPath"
}

Write-Success "Configurações removidas"

# ============================================================================
# 8. LIMPAR NSSM (OPCIONAL)
# ============================================================================

$cleanNSSM = Read-Host "`nDeseja remover o NSSM também? (S/N)"
if ($cleanNSSM -eq "S" -or $cleanNSSM -eq "s") {
    Write-Step "🗑️ Removendo NSSM..."
    
    if (Test-Path "C:\nssm") {
        Remove-Item -Path "C:\nssm" -Recurse -Force
        Write-Success "NSSM removido"
    }
}

# ============================================================================
# RESUMO FINAL
# ============================================================================

Write-Host "`n================================================" -ForegroundColor Green
Write-Host "      DESINSTALAÇÃO CONCLUÍDA COM SUCESSO!      " -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Host "O RPA Worker foi completamente removido do sistema." -ForegroundColor Cyan
Write-Host ""

if ($KeepLogs -or $KeepConfig) {
    Write-Host "📦 Backup salvo em:" -ForegroundColor Cyan
    Write-Host "   $backupPath"
    Write-Host ""
}

Write-Host "Obrigado por usar o RPA Worker!" -ForegroundColor Cyan
Write-Host ""