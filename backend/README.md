# 🚀 RPA Orchestrator - Estrutura Base

Plataforma de Orquestração de Automações RPA Multi-Tenant desenvolvida com FastAPI.

## 📁 Estrutura do Projeto

```
backend/
├── app/
│   ├── __init__.py                # Package principal
│   ├── main.py                    # ⭐ Aplicação FastAPI
│   │
│   ├── api/                       # Endpoints REST
│   │   ├── __init__.py
│   │   └── v1/                    # API versionada
│   │       ├── __init__.py
│   │       └── health.py          # ✅ Health checks
│   │
│   ├── core/                      # Módulos fundamentais
│   │   ├── __init__.py
│   │   ├── config.py              # ⚙️ Configurações
│   │   ├── database.py            # 🗄️ PostgreSQL
│   │   ├── redis.py               # 📦 Redis + Cache
│   │   ├── security.py            # 🔐 JWT + Auth
│   │   ├── exceptions.py          # ⚠️ Error handlers
│   │   ├── logging.py             # 📝 Logs estruturados
│   │   └── middlewares.py         # 🔧 Middlewares
│   │
│   ├── models/                    # 🏗️ SQLModel (TODO)
│   ├── schemas/                   # 📋 Pydantic schemas (TODO)
│   ├── services/                  # 💼 Business logic (TODO)
│   └── utils/                     # 🛠️ Utilitários (TODO)
│
├── requirements.txt               # Dependências Python
├── .env.example                   # Template de variáveis
├── .env                          # Suas configurações (criar)
└── test_structure.py             # Script de validação

```

## 🎯 O Que Foi Implementado

### ✅ Core Completo
- [x] **Config** - Gerenciamento de variáveis de ambiente com Pydantic
- [x] **Database** - Conexão assíncrona com PostgreSQL (SQLModel)
- [x] **Redis** - Conexão + sistema de cache completo
- [x] **Security** - JWT (access + refresh tokens), hashing de senhas
- [x] **Exceptions** - Handlers globais e exceções customizadas
- [x] **Logging** - Logs estruturados com correlation ID
- [x] **Middlewares** - Correlation ID, Request Logging, Rate Limiting

### ✅ API v1
- [x] **Health Checks** 
  - `GET /api/v1/health` - Health check básico
  - `GET /api/v1/health/detailed` - Com status de dependências
  - `GET /api/v1/health/ready` - Readiness probe (Kubernetes)
  - `GET /api/v1/health/live` - Liveness probe (Kubernetes)

### ✅ Aplicação Principal
- [x] **FastAPI** - Configuração completa com lifespan events
- [x] **CORS** - Configurado para desenvolvimento
- [x] **Documentação** - Swagger UI + ReDoc automáticos
- [x] **Multi-tenancy** - Estrutura preparada

## 🚀 Quick Start

### 1. Pré-requisitos

- Python 3.11+
- Docker + Docker Compose
- Git

### 2. Configurar Ambiente

```bash
# Clone o projeto (se ainda não tiver)
cd ~/Projects/BotManager/backend

# Crie o ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou
.venv\Scripts\activate  # Windows

# Instale as dependências
pip install -r requirements.txt
```

### 3. Configurar Variáveis de Ambiente

```bash
# Copie o template
cp .env.example .env

# Edite o .env e ajuste:
# - SECRET_KEY (IMPORTANTE: gere uma chave segura!)
# - DATABASE_URL (se necessário)
# - REDIS_URL (se necessário)
nano .env  # ou seu editor preferido
```

**⚠️ IMPORTANTE:** Gere uma SECRET_KEY segura:
```bash
# Gerar chave com OpenSSL
openssl rand -hex 32

# Ou com Python
python -c "import secrets; print(secrets.token_hex(32))"
```

### 4. Iniciar Containers (PostgreSQL + Redis)

```bash
# Do diretório raiz do projeto
cd ~/Projects/BotManager
docker compose up -d

# Verificar se estão rodando
docker compose ps
```

Você deve ver:
```
NAME                          STATUS
botmanager-postgres-1         Up (healthy)
botmanager-redis-1            Up (healthy)
```

### 5. Testar a Estrutura

```bash
# Volte para o diretório backend
cd backend

# Execute o script de validação
python test_structure.py
```

Se tudo estiver OK, você verá:
```
🎉 TODOS OS TESTES PASSARAM!
```

### 6. Rodar a Aplicação

```bash
# Modo development (com reload automático)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Ou simplesmente
python -m app.main
```

### 7. Acessar a Aplicação

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/api/v1/health
- **Health Detailed**: http://localhost:8000/api/v1/health/detailed

## 🧪 Testando os Endpoints

### Usando cURL

```bash
# Health check básico
curl http://localhost:8000/api/v1/health

# Health check detalhado
curl http://localhost:8000/api/v1/health/detailed

# Readiness probe
curl http://localhost:8000/api/v1/health/ready

# Liveness probe
curl http://localhost:8000/api/v1/health/live
```

### Usando HTTPie (mais bonito)

```bash
# Instalar httpie (opcional)
pip install httpie

# Testar endpoints
http GET localhost:8000/api/v1/health
http GET localhost:8000/api/v1/health/detailed
```

## 📊 Estrutura de Resposta

### Health Check Básico
```json
{
  "status": "healthy",
  "timestamp": "2024-12-09T10:00:00Z",
  "version": "v1",
  "environment": "development"
}
```

### Health Check Detalhado
```json
{
  "status": "healthy",
  "timestamp": "2024-12-09T10:00:00Z",
  "version": "v1",
  "environment": "development",
  "services": {
    "database": {
      "name": "PostgreSQL",
      "status": "connected",
      "latency_ms": 5.23
    },
    "redis": {
      "name": "Redis",
      "status": "connected",
      "latency_ms": 2.15
    }
  }
}
```

## 🔧 Configurações Importantes

### Variáveis de Ambiente (.env)

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `DATABASE_URL` | URL de conexão PostgreSQL | `postgresql+asyncpg://...` |
| `REDIS_URL` | URL de conexão Redis | `redis://localhost:6379/0` |
| `SECRET_KEY` | Chave para assinar JWT | **OBRIGATÓRIO** (min 32 chars) |
| `ENVIRONMENT` | Ambiente (development/staging/production) | `development` |
| `LOG_LEVEL` | Nível de log | `INFO` |
| `RATE_LIMIT_PER_MINUTE` | Limite de requests por minuto | `100` |

### CORS

Por padrão, aceita requests de:
- http://localhost:3000 (frontend React/Next.js)
- http://localhost:8000 (Swagger UI)
- http://localhost:5173 (Vite dev server)

Edite `CORS_ORIGINS` no `.env` para adicionar outras origens.

## 🐛 Troubleshooting

### Erro: "Cannot connect to PostgreSQL"

```bash
# Verificar se container está rodando
docker compose ps

# Ver logs do PostgreSQL
docker compose logs postgres

# Reiniciar containers
docker compose restart
```

### Erro: "Cannot connect to Redis"

```bash
# Verificar se container está rodando
docker compose ps

# Ver logs do Redis
docker compose logs redis

# Reiniciar containers
docker compose restart
```

### Erro: "SECRET_KEY deve ter pelo menos 32 caracteres"

```bash
# Gere uma chave segura
openssl rand -hex 32

# Ou com Python
python -c "import secrets; print(secrets.token_hex(32))"

# Cole no .env
SECRET_KEY=sua_chave_gerada_aqui
```

### Erro de Import

```bash
# Certifique-se de estar no diretório correto
cd ~/Projects/BotManager/backend

# E que o ambiente virtual está ativado
source .venv/bin/activate

# Reinstale dependências se necessário
pip install -r requirements.txt
```

## 📝 Logs

A aplicação gera logs estruturados com:
- **Correlation ID** - Para rastrear requests
- **Timestamp** - Em formato ISO 8601
- **Level** - DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Context** - Informações adicionais (tenant_id, user_id, etc.)

### Formato em Development
```
[2024-12-09 10:00:00] [INFO] [abc12345...] app.main: Application started
```

### Formato em Production (JSON)
```json
{
  "timestamp": "2024-12-09T10:00:00Z",
  "level": "INFO",
  "logger": "app.main",
  "message": "Application started",
  "correlation_id": "abc12345-6789-..."
}
```

## 🎯 Próximos Passos

1. **Modelos de Banco de Dados**
   - Criar modelos SQLModel para as 12 tabelas
   - Configurar Alembic para migrations
   - Implementar relacionamentos

2. **Autenticação de Usuários**
   - Endpoint de login
   - Endpoint de registro
   - Refresh token
   - Validação de permissões

3. **Endpoints de Negócio**
   - CRUD de Agentes
   - CRUD de Processos
   - Gerenciamento de Execuções
   - Gerenciamento de Filas

4. **Testes**
   - Testes unitários com pytest
   - Testes de integração
   - Testes de carga

5. **Deployment**
   - Dockerfile otimizado
   - Docker Compose para produção
   - CI/CD pipeline
   - Kubernetes manifests

## 📚 Documentação de Referência

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [SQLModel Docs](https://sqlmodel.tiangolo.com/)
- [Pydantic Docs](https://docs.pydantic.dev/)
- [Redis Python Docs](https://redis-py.readthedocs.io/)

## 💡 Dicas

### Hot Reload
O servidor reinicia automaticamente ao detectar mudanças nos arquivos Python quando rodando com `--reload`.

### Explorar a API
Acesse `/docs` para testar todos os endpoints interativamente com Swagger UI.

### Logs em Tempo Real
```bash
# No mesmo terminal que está rodando uvicorn
# ou use outro terminal:
tail -f app.log  # se configurar log em arquivo
```

### Debug no VSCode
Adicione ao `.vscode/launch.json`:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": ["app.main:app", "--reload"],
      "jinja": true
    }
  ]
}
```

---

## ✅ Checklist de Validação

- [ ] Containers Docker rodando (PostgreSQL + Redis)
- [ ] Ambiente virtual ativado
- [ ] Dependências instaladas
- [ ] Arquivo .env configurado com SECRET_KEY válida
- [ ] Script de teste passou (`python test_structure.py`)
- [ ] Aplicação rodando (`uvicorn app.main:app --reload`)
- [ ] Health check respondendo (http://localhost:8000/api/v1/health)
- [ ] Docs acessíveis (http://localhost:8000/docs)

---

**🎉 Pronto! Sua estrutura base está funcionando!**

Qualquer dúvida, consulte os logs ou o código-fonte - está tudo bem documentado.


# 🚀 RPA Orchestrator - Backend

Plataforma de Orquestração de Automações RPA Multi-Tenant desenvolvida com FastAPI.

## 📁 Estrutura do Projeto
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # ⭐ Aplicação FastAPI
│   │
│   ├── api/                       # Endpoints REST
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── health.py          # Health checks
│   │
│   ├── core/                      # Módulos fundamentais
│   │   ├── __init__.py
│   │   ├── config.py              # Configurações
│   │   ├── database.py            # PostgreSQL
│   │   ├── redis.py               # Redis + Cache
│   │   ├── security.py            # JWT + Auth
│   │   ├── exceptions.py          # Error handlers
│   │   ├── logging.py             # Logs estruturados
│   │   └── middlewares.py         # Middlewares
│   │
│   ├── models/                    # SQLModel (TODO)
│   ├── schemas/                   # Pydantic schemas (TODO)
│   ├── services/                  # Business logic (TODO)
│   └── utils/                     # Utilitários (TODO)
│
├── requirements.txt
├── .env.example
├── .env
└── test_structure.py
```

## 🚀 Quick Start

### 1. Configurar Ambiente
```bash
cd ~/Projects/BotManager/backend

# Ative o ambiente virtual
source .venv/bin/activate

# Instale as dependências
pip install -r requirements.txt
```

### 2. Configurar Variáveis de Ambiente
```bash
# Copie o template
cp .env.example .env

# Gere uma SECRET_KEY segura
openssl rand -hex 32

# Edite o .env e cole a SECRET_KEY
nano .env
```

### 3. Iniciar Containers
```bash
cd ~/Projects/BotManager
docker compose up -d

# Verificar status
docker compose ps
```

### 4. Testar Estrutura
```bash
cd backend
python test_structure.py
```

### 5. Rodar Aplicação
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Acessar Documentação

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/api/v1/health

## 🧪 Testando Endpoints
```bash
# Health check básico
curl http://localhost:8000/api/v1/health

# Health check detalhado
curl http://localhost:8000/api/v1/health/detailed

# Readiness probe
curl http://localhost:8000/api/v1/health/ready

# Liveness probe
curl http://localhost:8000/api/v1/health/live
```

## 🔧 Configurações Importantes

### Variáveis de Ambiente (.env)

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `DATABASE_URL` | URL de conexão PostgreSQL | `postgresql+asyncpg://...` |
| `REDIS_URL` | URL de conexão Redis | `redis://localhost:6379/0` |
| `SECRET_KEY` | Chave para assinar JWT | **OBRIGATÓRIO** (min 32 chars) |
| `ENVIRONMENT` | Ambiente | `development` |
| `LOG_LEVEL` | Nível de log | `INFO` |

## 🐛 Troubleshooting

### Erro: "Cannot connect to PostgreSQL"
```bash
docker compose ps
docker compose logs postgres
docker compose restart
```

### Erro: "SECRET_KEY deve ter pelo menos 32 caracteres"
```bash
# Gere uma chave segura
openssl rand -hex 32

# Cole no .env
SECRET_KEY=sua_chave_aqui
```

## 🎯 Próximos Passos

1. Criar modelos SQLModel (12 tabelas)
2. Configurar Alembic para migrations
3. Implementar endpoints de autenticação
4. Criar endpoints de negócio (Agentes, Processos, etc.)

---

**Desenvolvido com ❤️ pela equipe RPA Orchestrator**