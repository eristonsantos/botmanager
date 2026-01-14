# 🤖 RPA Worker - Complete Package

Sistema completo de Worker RPA com interface desktop e serviço Windows.

## 📦 Conteúdo do Pacote
```
rpa-worker-package/
├── worker/              # Python Worker Service
├── ui/                  # Tauri Desktop App  
├── installer/           # Scripts de instalação
└── README.md
```

## 🚀 Instalação Rápida

### Pré-requisitos

- Windows 10/11
- Python 3.11+
- Rust (para build da UI - opcional)

### Instalação Automática
```powershell
# Execute como Administrador
.\installer\install.ps1
```

Isso irá:
- ✅ Instalar Worker Python como serviço Windows
- ✅ Configurar startup automático
- ✅ Instalar UI Desktop
- ✅ Criar atalhos
- ✅ Configurar firewall

## ⚙️ Configuração

Após instalação, edite `C:\RpaWorker\.env`:
```env
WORKER_NAME=RPA-Worker-01
ORCHESTRATOR_URL=http://seu-servidor:8000
API_KEY=sua-api-key-aqui
TENANT_ID=seu-tenant-id-aqui
```

Reinicie o serviço:
```powershell
nssm restart RpaWorker
```

## 🎮 Uso

### Interface Desktop

- Busque "RPA Worker" no Menu Iniciar
- Ou execute: `C:\RpaWorker\RpaWorkerUI.exe`

### Controle via PowerShell
```powershell
# Iniciar
nssm start RpaWorker

# Parar
nssm stop RpaWorker

# Status
Get-Service RpaWorker

# Logs
Get-Content C:\RpaWorker\logs\worker.log -Tail 50
```

### API Local
```powershell
# Status
curl http://localhost:8765/status

# Iniciar worker
curl -X POST http://localhost:8765/start

# Parar worker
curl -X POST http://localhost:8765/stop
```

## 🔄 Atualização
```powershell
# Execute como Administrador
.\installer\update.ps1
```

## 🗑️ Desinstalação
```powershell
# Execute como Administrador
.\installer\uninstall.ps1

# Manter logs e configurações
.\installer\uninstall.ps1 -KeepLogs -KeepConfig
```

## 🛠️ Desenvolvimento

### Build Worker
```bash
cd worker
pip install -r requirements.txt
python main.py
```

### Build UI
```powershell
cd ui
.\build.ps1
```

### Dev Mode (UI)
```powershell
cd ui
.\dev.ps1
```

## 📝 Logs

Logs do serviço:
- `C:\RpaWorker\logs\worker.log`
- `C:\RpaWorker\logs\stdout.log`
- `C:\RpaWorker\logs\stderr.log`

## 🔧 Troubleshooting

### Serviço não inicia
```powershell
# Verifique logs
Get-Content C:\RpaWorker\logs\stderr.log

# Teste manualmente
cd C:\RpaWorker
python main.py
```

### API não responde
```powershell
# Verifique se porta 8765 está livre
netstat -ano | findstr 8765

# Teste conectividade
Test-NetConnection -ComputerName localhost -Port 8765
```

### UI não abre

- Verifique se o serviço está rodando
- Reinstale: `.\installer\install.ps1 -SkipService`

## 📚 Arquitetura
```
┌─────────────────┐
│  Tauri UI       │ ← Interface Desktop
│  (Rust + HTML)  │
└────────┬────────┘
         │ HTTP
         ↓
┌─────────────────┐
│  Python Worker  │ ← Serviço Windows
│  (FastAPI)      │
└────────┬────────┘
         │ Polling
         ↓
┌─────────────────┐
│  Orquestrador   │ ← Sua API Backend
│  (Backend)      │
└─────────────────┘
```

## 🤝 Suporte

- 📧 Email: suporte@seudominio.com
- 📚 Docs: https://docs.seudominio.com
- 🐛 Issues: https://github.com/seu-repo/issues

## 📄 Licença

Proprietário - Todos os direitos reservados

---

**Desenvolvido com ❤️ pela equipe COGNTIX by Brain**