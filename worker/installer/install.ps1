# installer/install.ps1
# Script principal de instalação do RPA Worker

#Requires -RunAsAdministrator

param(
    [string]$InstallPath = "C:\RpaWorker",
    [switch]$SkipService = $false,
    [switch]$SkipUI = $false
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
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "       RPA WORKER - INSTALADOR v1.0.0          " -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# 1. VERIFICAR PRÉ-REQUISITOS
# ============================================================================

Write-Step "🔍 Verificando pré-requisitos..."

# Python
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Error "Python não encontrado. Instale Python 3.11+ em: https://www.python.org/"
    exit 1
}

$pythonVersion = & python --version
Write-Host "   Python: $pythonVersion"

# Pip
$pipCmd = Get-Command pip -ErrorAction SilentlyContinue
if (-not $pipCmd) {
    Write-Error "pip não encontrado. Reinstale o Python com pip incluído."
    exit 1
}

Write-Success "Pré-requisitos OK"

# ============================================================================
# 2. CRIAR ESTRUTURA DE DIRETÓRIOS
# ============================================================================

Write-Step "📁 Criando estrutura de diretórios..."

$directories = @(
    $InstallPath,
    "$InstallPath\logs",
    "$InstallPath\config",
    "$InstallPath\automations"
)

foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "   Criado: $dir"
    }
}

Write-Success "Diretórios criados"

# ============================================================================
# 3. COPIAR ARQUIVOS PYTHON
# ============================================================================

Write-Step "📦 Copiando arquivos do Worker..."

$workerFiles = @(
    "worker\main.py",
    "worker\manager.py",
    "worker\automation_runner.py",
    "worker\config.py",
    "worker\requirements.txt",
    "worker\.env.example"
)

foreach ($file in $workerFiles) {
    if (Test-Path $file) {
        Copy-Item -Path $file -Destination $InstallPath -Force
        Write-Host "   Copiado: $(Split-Path $file -Leaf)"
    } else {
        Write-Warning "Arquivo não encontrado: $file"
    }
}

# Cria .env se não existir
$envPath = "$InstallPath\.env"
if (-not (Test-Path $envPath)) {
    Copy-Item -Path "$InstallPath\.env.example" -Destination $envPath -Force
    Write-Host "   Criado: .env (configure depois)"
}

Write-Success "Arquivos copiados"

# ============================================================================
# 4. INSTALAR DEPENDÊNCIAS PYTHON
# ============================================================================

Write-Step "🐍 Instalando dependências Python..."

Push-Location $InstallPath
& python -m pip install --upgrade pip
& pip install -r requirements.txt
Pop-Location

Write-Success "Dependências instaladas"

# ============================================================================
# 5. INSTALAR NSSM (Service Manager)
# ============================================================================

if (-not $SkipService) {
    Write-Step "⚙️ Instalando NSSM (Service Manager)..."
    
    $nssmPath = "C:\nssm"
    $nssmExe = "$nssmPath\nssm.exe"
    
    if (-not (Test-Path $nssmExe)) {
        # Copia NSSM do installer
        if (Test-Path "installer\nssm.exe") {
            New-Item -ItemType Directory -Path $nssmPath -Force | Out-Null
            Copy-Item -Path "installer\nssm.exe" -Destination $nssmExe -Force
            Write-Host "   NSSM copiado para: $nssmExe"
        } else {
            Write-Warning "nssm.exe não encontrado em installer\"
            Write-Host "   Baixe em: https://nssm.cc/download"
            Write-Host "   Coloque em: installer\nssm.exe"
            exit 1
        }
    } else {
        Write-Host "   NSSM já instalado"
    }
    
    Write-Success "NSSM instalado"
}

# ============================================================================
# 6. INSTALAR SERVIÇO WINDOWS
# ============================================================================

if (-not $SkipService) {
    Write-Step "🔧 Instalando serviço Windows..."
    
    $serviceName = "RpaWorker"
    $pythonPath = (Get-Command python).Source
    $scriptPath = "$InstallPath\main.py"
    
    # Remove serviço existente se houver
    $existingService = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
    if ($existingService) {
        Write-Host "   Removendo serviço existente..."
        & $nssmExe stop $serviceName
        & $nssmExe remove $serviceName confirm
    }
    
    # Instala novo serviço
    & $nssmExe install $serviceName $pythonPath $scriptPath
    & $nssmExe set $serviceName AppDirectory $InstallPath
    & $nssmExe set $serviceName DisplayName "RPA Worker Service"
    & $nssmExe set $serviceName Description "Serviço de Worker RPA para execução de automações"
    & $nssmExe set $serviceName Start SERVICE_AUTO_START
    & $nssmExe set $serviceName AppStdout "$InstallPath\logs\stdout.log"
    & $nssmExe set $serviceName AppStderr "$InstallPath\logs\stderr.log"
    & $nssmExe set $serviceName AppStdoutCreationDisposition 4
    & $nssmExe set $serviceName AppStderrCreationDisposition 4
    & $nssmExe set $serviceName AppRotateFiles 1
    & $nssmExe set $serviceName AppRotateBytes 10485760  # 10MB
    
    Write-Success "Serviço instalado"
    
    # Inicia serviço
    Write-Host "`n   Iniciando serviço..."
    & $nssmExe start $serviceName
    Start-Sleep -Seconds 2
    
    $service = Get-Service -Name $serviceName
    if ($service.Status -eq "Running") {
        Write-Success "Serviço iniciado com sucesso"
    } else {
        Write-Warning "Serviço instalado mas não iniciou. Verifique os logs."
    }
}

# ============================================================================
# 7. INSTALAR UI (TAURI APP)
# ============================================================================

if (-not $SkipUI) {
    Write-Step "🖥️ Instalando UI (Tauri App)..."
    
    $uiExe = "ui\src-tauri\target\release\rpa-worker-ui.exe"
    
    if (Test-Path $uiExe) {
        # Copia executável
        Copy-Item -Path $uiExe -Destination "$InstallPath\RpaWorkerUI.exe" -Force
        Write-Host "   UI copiada para: $InstallPath\RpaWorkerUI.exe"
        
        # Cria atalho no Menu Iniciar
        $WshShell = New-Object -ComObject WScript.Shell
        $Shortcut = $WshShell.CreateShortcut("$env:APPDATA\Microsoft\Windows\Start Menu\Programs\RPA Worker.lnk")
        $Shortcut.TargetPath = "$InstallPath\RpaWorkerUI.exe"
        $Shortcut.WorkingDirectory = $InstallPath
        $Shortcut.Description = "RPA Worker Control Panel"
        $Shortcut.Save()
        
        Write-Success "UI instalada"
        Write-Host "   Atalho criado no Menu Iniciar"
        
    } else {
        Write-Warning "UI não encontrada. Build primeiro com: ui\build.ps1"
    }
}

# ============================================================================
# 8. CONFIGURAÇÃO DE FIREWALL
# ============================================================================

Write-Step "🔥 Configurando Firewall..."

$firewallRule = Get-NetFirewallRule -DisplayName "RPA Worker API" -ErrorAction SilentlyContinue

if (-not $firewallRule) {
    New-NetFirewallRule `
        -DisplayName "RPA Worker API" `
        -Direction Inbound `
        -LocalPort 8765 `
        -Protocol TCP `
        -Action Allow `
        -Profile Private | Out-Null
    
    Write-Success "Regra de firewall criada (porta 8765)"
} else {
    Write-Host "   Regra de firewall já existe"
}

# ============================================================================
# RESUMO FINAL
# ============================================================================

Write-Host "`n================================================" -ForegroundColor Green
Write-Host "       INSTALAÇÃO CONCLUÍDA COM SUCESSO!        " -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Host "📍 Instalação:" -ForegroundColor Cyan
Write-Host "   $InstallPath"
Write-Host ""
Write-Host "🔧 Serviço Windows:" -ForegroundColor Cyan
Write-Host "   Nome: RpaWorker"
Write-Host "   Status: Rodando"
Write-Host "   API: http://localhost:8765"
Write-Host ""
Write-Host "🖥️ Interface UI:" -ForegroundColor Cyan
Write-Host "   Busque 'RPA Worker' no Menu Iniciar"
Write-Host "   Ou execute: $InstallPath\RpaWorkerUI.exe"
Write-Host ""
Write-Host "⚙️ Configuração:" -ForegroundColor Cyan
Write-Host "   Edite: $InstallPath\.env"
Write-Host "   Configure:"
Write-Host "     - ORCHESTRATOR_URL (URL da API backend)"
Write-Host "     - API_KEY (chave de autenticação)"
Write-Host "     - TENANT_ID (ID do seu tenant)"
Write-Host ""
Write-Host "📝 Logs:" -ForegroundColor Cyan
Write-Host "   $InstallPath\logs\"
Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Pergunta se quer abrir a UI
$openUI = Read-Host "Deseja abrir o painel de controle agora? (S/N)"
if ($openUI -eq "S" -or $openUI -eq "s") {
    if (Test-Path "$InstallPath\RpaWorkerUI.exe") {
        Start-Process "$InstallPath\RpaWorkerUI.exe"
    }
}