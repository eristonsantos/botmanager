# 🍎 Guia de Preparação do Ambiente - macOS

> **Guia completo para configurar o ambiente de desenvolvimento do RPA Orchestrator no macOS**

---

## 📋 Índice

1. [Pré-requisitos](#pré-requisitos)
2. [Instalação do Homebrew](#1-instalação-do-homebrew)
3. [Instalação do Docker Desktop](#2-instalação-do-docker-desktop)
4. [Instalação do Python 3.11+](#3-instalação-do-python-311)
5. [Instalação do Git](#4-instalação-do-git)
6. [Instalação do VS Code](#5-instalação-do-vs-code)
7. [Ferramentas CLI Úteis](#6-ferramentas-cli-úteis)
8. [Configuração do Projeto](#7-configuração-do-projeto)
9. [Configuração do Docker](#8-configuração-do-docker)
10. [Verificação Final](#9-verificação-final)
11. [Comandos do Dia a Dia](#10-comandos-do-dia-a-dia)
12. [Solução de Problemas](#11-solução-de-problemas)

---

## Pré-requisitos

- macOS Monterey (12.0) ou superior
- 8GB RAM mínimo (16GB recomendado)
- 20GB de espaço em disco livre
- Conexão com internet
- Privilégios de administrador

---

## 1️⃣ Instalação do Homebrew

Homebrew é o gerenciador de pacotes essencial para macOS.

```bash
# Verificar se já está instalado
brew --version

# Se não estiver instalado, executar:
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Seguir as instruções para adicionar ao PATH
# Geralmente adiciona automaticamente ao ~/.zprofile
```

### Verificar instalação
```bash
brew --version
# Deve mostrar: Homebrew 4.x.x
```

---

## 2️⃣ Instalação do Docker Desktop

### Via Homebrew (Recomendado)

```bash
# Instalar Docker Desktop
brew install --cask docker

# Abrir Docker Desktop pela primeira vez
open /Applications/Docker.app
```

### Via Download Manual

1. Acesse: https://www.docker.com/products/docker-desktop
2. Clique em **"Download for Mac"**
3. Escolha a versão correta:
   - **Apple Silicon** (M1/M2/M3/M4)
   - **Intel Chip**
4. Instale o `.dmg` e arraste para Applications
5. Abra o Docker Desktop

### Configuração Inicial do Docker

1. Ao abrir pela primeira vez, escolha: **"Use recommended settings"**
2. Digite sua senha do Mac quando solicitado
3. Aguarde 30-60 segundos até o ícone da baleia aparecer na barra superior
4. Configure para iniciar automaticamente:
   - Clique no ícone do Docker na barra superior
   - Vá em **Settings (⚙️)** → **General**
   - ✅ Marque: **"Start Docker Desktop when you log in"**

### Verificar instalação

```bash
# Verificar versão do Docker
docker --version
# Deve mostrar: Docker version 24.x.x ou superior

# Verificar versão do Docker Compose
docker compose version
# Deve mostrar: Docker Compose version v2.x.x

# Testar com hello-world
docker run hello-world
```

---

## 3️⃣ Instalação do Python 3.11+

### Com pyenv (Se já estiver instalado)

```bash
# Verificar se pyenv está instalado
pyenv --version

# Se estiver instalado, configurar:
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc
echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc
echo 'eval "$(pyenv init -)"' >> ~/.zshrc
source ~/.zshrc

# Definir Python 3.11.10 como versão global
pyenv global 3.11.10
```

### Via Homebrew (Alternativa)

```bash
# Instalar Python 3.11
brew install python@3.11

# Criar aliases úteis (opcional)
echo 'alias python=python3.11' >> ~/.zshrc
echo 'alias pip=pip3' >> ~/.zshrc
source ~/.zshrc
```

### Verificar instalação

```bash
python --version
# Deve mostrar: Python 3.11.x

pip --version
# Deve mostrar: pip 24.x (python 3.11)
```

---

## 4️⃣ Instalação do Git

```bash
# Verificar se já está instalado (geralmente vem no macOS)
git --version

# Se não estiver instalado
brew install git

# Configurar credenciais globais
git config --global user.name "Seu Nome"
git config --global user.email "seu@email.com"

# Verificar configuração
git config --list
```

---

## 5️⃣ Instalação do VS Code

### Via Homebrew

```bash
brew install --cask visual-studio-code
```

### Via Download Manual

1. Acesse: https://code.visualstudio.com/
2. Baixe e instale

### Extensões Essenciais

Abra o VS Code e instale (Cmd+Shift+X):

- **Python** (Microsoft)
- **Pylance** (Microsoft)
- **Docker** (Microsoft)
- **SQLTools** (Matheus Teixeira) - Para conectar no PostgreSQL
- **SQLTools PostgreSQL Driver** (Matheus Teixeira)
- **REST Client** (Huachao Mao) - Para testar APIs
- **Thunder Client** (Thunder Client) - Alternativa ao Postman

### Configurar VS Code no Terminal

```bash
# Adicionar 'code' ao PATH
# No VS Code: Cmd+Shift+P → "Shell Command: Install 'code' command in PATH"

# Testar
code --version
```

---

## 6️⃣ Ferramentas CLI Úteis

```bash
# HTTPie - Cliente HTTP moderno
brew install httpie

# jq - Processar JSON no terminal
brew install jq

# PostgreSQL Client
brew install libpq
echo 'export PATH="/opt/homebrew/opt/libpq/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# Tree - Visualizar estrutura de pastas
brew install tree

# Redis CLI (para testar Redis)
brew install redis

# Verificar instalações
http --version
jq --version
psql --version
tree --version
redis-cli --version
```

---

## 7️⃣ Configuração do Projeto

### Criar estrutura do projeto

```bash
# Criar diretório do projeto
mkdir -p ~/Projects/rpa-orchestrator
cd ~/Projects/rpa-orchestrator

# Inicializar Git
git init

# Criar estrutura de pastas
mkdir -p backend/app/{api,core,models,services,utils}
mkdir -p backend/alembic/versions
mkdir -p docker/postgres
mkdir -p docs
mkdir -p tests

# Criar arquivos essenciais
touch backend/requirements.txt
touch backend/Dockerfile
touch docker-compose.yml
touch .env.example
touch .gitignore
touch README.md
```

### Criar .gitignore

```bash
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
.venv/
venv/
env/
ENV/

# Environment variables
.env
.env.local

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Database
*.db
*.sqlite3

# Docker
docker-compose.override.yml

# Logs
logs/
*.log

# Alembic
alembic/versions/*.pyc

# Testing
.pytest_cache/
.coverage
htmlcov/

# Build
dist/
build/
*.egg-info/
EOF
```

### Criar requirements.txt

```bash
cat > backend/requirements.txt << 'EOF'
# Core Framework
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.5.3
pydantic-settings==2.1.0

# Database
sqlmodel==0.0.14
psycopg2-binary==2.9.9
alembic==1.13.1

# Redis
redis==5.0.1
hiredis==2.3.2

# Security
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6

# HTTP Client
httpx==0.26.0

# Utilities
python-dotenv==1.0.0
tenacity==8.2.3

# Development
pytest==7.4.4
pytest-asyncio==0.23.3
black==24.1.1
ruff==0.1.14
EOF
```

### Criar Virtual Environment

```bash
cd ~/Projects/rpa-orchestrator/backend

# Criar ambiente virtual
python -m venv .venv

# Ativar ambiente virtual
source .venv/bin/activate

# Atualizar pip
pip install --upgrade pip

# Instalar dependências
pip install -r requirements.txt

# Verificar instalação
pip list
```

### Criar alias útil

```bash
# Adicionar ao ~/.zshrc
echo 'alias venv="source .venv/bin/activate"' >> ~/.zshrc
source ~/.zshrc

# Agora você pode ativar o ambiente com:
cd ~/Projects/rpa-orchestrator/backend
venv
```

---

## 8️⃣ Configuração do Docker

### Criar docker-compose.yml

```bash
cd ~/Projects/rpa-orchestrator

cat > docker-compose.yml << 'EOF'
services:
  postgres:
    image: postgres:16-alpine
    container_name: rpa-postgres
    environment:
      POSTGRES_USER: rpa_admin
      POSTGRES_PASSWORD: rpa_dev_2024
      POSTGRES_DB: rpa_orchestrator
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U rpa_admin"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: rpa-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

volumes:
  postgres_data:
  redis_data:
EOF
```

### Criar .env.example

```bash
cat > .env.example << 'EOF'
# Database
DATABASE_URL=postgresql://rpa_admin:rpa_dev_2024@localhost:5432/rpa_orchestrator

# Redis
REDIS_URL=redis://localhost:6379/0

# API
SECRET_KEY=your-secret-key-here-min-32-chars-CHANGE-IN-PRODUCTION
ENVIRONMENT=development
API_VERSION=v1

# Multi-Tenant
DEFAULT_TENANT_ID=default

# Logging
LOG_LEVEL=INFO
EOF

# Copiar para .env
cp .env.example .env
```

### Subir os containers

```bash
# Subir PostgreSQL + Redis
docker compose up -d

# Verificar status
docker compose ps

# Ver logs
docker compose logs -f
```

---

## 9️⃣ Verificação Final

Execute este script para verificar tudo:

```bash
#!/bin/bash

echo "🔍 Verificando instalação do ambiente..."
echo ""

echo "=== Homebrew ==="
brew --version || echo "❌ Homebrew não instalado"
echo ""

echo "=== Docker ==="
docker --version || echo "❌ Docker não instalado"
docker compose version || echo "❌ Docker Compose não instalado"
echo ""

echo "=== Python ==="
python --version || echo "❌ Python não instalado"
pip --version || echo "❌ Pip não instalado"
echo ""

echo "=== Git ==="
git --version || echo "❌ Git não instalado"
echo ""

echo "=== Ferramentas CLI ==="
http --version || echo "⚠️ HTTPie não instalado"
jq --version || echo "⚠️ jq não instalado"
psql --version || echo "⚠️ PostgreSQL client não instalado"
redis-cli --version || echo "⚠️ Redis CLI não instalado"
tree --version || echo "⚠️ Tree não instalado"
echo ""

echo "=== Containers Docker ==="
docker compose ps 2>/dev/null || echo "⚠️ Containers não estão rodando"
echo ""

echo "=== Testar PostgreSQL ==="
psql postgresql://rpa_admin:rpa_dev_2024@localhost:5432/rpa_orchestrator -c "SELECT version();" 2>/dev/null && echo "✅ PostgreSQL OK" || echo "❌ PostgreSQL não acessível"
echo ""

echo "=== Testar Redis ==="
redis-cli ping 2>/dev/null && echo "✅ Redis OK" || echo "❌ Redis não acessível"
echo ""

echo "✅ Verificação concluída!"
```

---

## 🔟 Comandos do Dia a Dia

### Workflow completo de desenvolvimento

```bash
# 1. Navegar até o projeto
cd ~/Projects/rpa-orchestrator

# 2. Ativar ambiente Python
source backend/.venv/bin/activate
# ou simplesmente:
venv

# 3. Subir infraestrutura (PostgreSQL + Redis)
docker compose up -d

# 4. Verificar se está tudo rodando
docker compose ps

# 5. Desenvolver...
cd backend
# Rodar API (quando estiver pronta):
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 6. Ao finalizar o trabalho
docker compose down
deactivate  # desativar ambiente Python
```

### Comandos Docker úteis

```bash
# Ver logs em tempo real
docker compose logs -f

# Ver logs de um serviço específico
docker compose logs -f postgres
docker compose logs -f redis

# Parar serviços
docker compose stop

# Parar e remover containers
docker compose down

# Parar, remover containers E volumes (CUIDADO: apaga dados!)
docker compose down -v

# Reiniciar um serviço específico
docker compose restart postgres

# Acessar shell do PostgreSQL
docker compose exec postgres psql -U rpa_admin -d rpa_orchestrator

# Acessar Redis CLI
docker compose exec redis redis-cli

# Ver uso de recursos dos containers
docker stats
```

### Comandos Python úteis

```bash
# Instalar nova dependência
pip install nome-pacote
pip freeze > requirements.txt  # Atualizar requirements

# Rodar testes
pytest

# Formatação de código
black .
ruff check .

# Criar migration (Alembic)
alembic revision --autogenerate -m "descrição"
alembic upgrade head
```

---

## 1️⃣1️⃣ Solução de Problemas

### Docker Desktop não inicia

```bash
# Forçar kill de processos antigos
killall Docker

# Tentar abrir novamente
open /Applications/Docker.app

# Aguardar 30-60 segundos
```

### Erro: "Cannot connect to Docker daemon"

**Solução**: O Docker Desktop não está rodando. Abra o aplicativo manualmente:
```bash
open /Applications/Docker.app
```

### Porta 5432 ou 6379 já em uso

```bash
# Ver processos usando a porta
sudo lsof -i :5432
sudo lsof -i :6379

# Parar processo específico
kill -9 <PID>

# Ou mudar a porta no docker-compose.yml:
# "5433:5432" ao invés de "5432:5432"
```

### pyenv: python3.11: command not found

```bash
# Configurar pyenv no shell
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc
echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc
echo 'eval "$(pyenv init -)"' >> ~/.zshrc
source ~/.zshrc

# Definir versão
pyenv global 3.11.10
```

### Virtual environment não ativa

```bash
# Certifique-se de estar no diretório correto
cd ~/Projects/rpa-orchestrator/backend

# Ativar explicitamente
source .venv/bin/activate

# Verificar
which python
```

### Problemas com dependências Python

```bash
# Limpar e reinstalar
rm -rf .venv
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Docker Compose: "version is obsolete"

```bash
# Remover linha "version: '3.8'" do docker-compose.yml
sed -i '' '/^version:/d' docker-compose.yml
```

---

## 📚 Recursos Adicionais

### Documentação Oficial

- **FastAPI**: https://fastapi.tiangolo.com/
- **SQLModel**: https://sqlmodel.tiangolo.com/
- **Docker**: https://docs.docker.com/
- **PostgreSQL**: https://www.postgresql.org/docs/
- **Redis**: https://redis.io/docs/

### Ferramentas Recomendadas

- **Postman/Insomnia**: Testar APIs
- **DBeaver**: Cliente visual para PostgreSQL
- **RedisInsight**: Cliente visual para Redis
- **Docker Desktop**: Interface gráfica para containers

---

## ✅ Checklist Final

Antes de começar o desenvolvimento, verifique:

- [ ] Homebrew instalado e funcionando
- [ ] Docker Desktop instalado e rodando
- [ ] Python 3.11+ instalado
- [ ] Git configurado com suas credenciais
- [ ] VS Code instalado com extensões
- [ ] Ferramentas CLI instaladas (httpie, jq, psql, redis-cli, tree)
- [ ] Estrutura do projeto criada
- [ ] Virtual environment Python criado e ativado
- [ ] Dependências Python instaladas
- [ ] docker-compose.yml criado
- [ ] Containers PostgreSQL e Redis rodando (healthy)
- [ ] Conexão com PostgreSQL funcionando
- [ ] Conexão com Redis funcionando

---

## 🎯 Próximos Passos

Após concluir este setup, você está pronto para:

1. **Criar a aplicação FastAPI** (`backend/app/main.py`)
2. **Definir modelos SQLModel** (tabelas do banco de dados)
3. **Configurar Alembic** (migrations)
4. **Implementar autenticação e multi-tenancy**
5. **Criar endpoints da API**

---

## 📞 Suporte

Se encontrar problemas durante a configuração:

1. Verifique a seção [Solução de Problemas](#11-solução-de-problemas)
2. Consulte a documentação oficial das ferramentas
3. Execute o script de verificação para identificar o que está faltando

---

**Desenvolvido para o projeto RPA Orchestrator** 🤖

Última atualização: Dezembro 2025