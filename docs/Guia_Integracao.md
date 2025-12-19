# 🚀 FASE 5A: Guia de Integração

Integração completa de Processos + Versionamento no seu projeto.

---

## 📁 Estrutura de Arquivos

```
backend/app/
├── schemas/
│   ├── __init__.py                (atualizar - adicionar imports)
│   ├── common.py                  (✅ já existe)
│   ├── agent.py                   (✅ ATUALIZAR - FIX #1 metadata→extra_data)
│   ├── auth.py                    (✅ já existe)
│   └── process.py                 (🆕 NOVO - Fase 5A)
│
├── services/
│   ├── __init__.py                (✅ já existe)
│   ├── agent_service.py           (✅ ATUALIZAR - FIX #2)
│   └── process_service.py         (🆕 NOVO - Fase 5A)
│
├── api/v1/
│   ├── __init__.py                (✅ ATUALIZAR - registrar processes router)
│   ├── health.py                  (✅ já existe)
│   ├── agents.py                  (✅ já existe)
│   └── processes.py               (🆕 NOVO - Fase 5A)
│
├── core/
│   ├── security/
│   │   ├── __init__.py            (✅ já existe)
│   │   ├── auth.py                (✅ ATUALIZAR - FIX #3 tenant_id do JWT)
│   │   ├── password.py            (✅ já existe)
│   │   └── encryption.py          (✅ já existe)
│   └── ...
│
└── models/
    ├── __init__.py                (✅ já existe)
    ├── base.py                    (✅ já existe)
    ├── core.py                    (✅ já existe - Processo, VersaoProcesso)
    └── ...
```

---

## 🔧 Passo 1: Aplicar os 3 Fixes

### Fix #1: schemas/agent.py
- Renomear `metadata` → `extra_data` em `AgentBase`, `AgentUpdate`, `HeartbeatRequest`
- Arquivo corrigido: `01_agent_schema_FIXED.py`

```bash
# Copiar o arquivo fixo
cp 01_agent_schema_FIXED.py backend/app/schemas/agent.py
```

### Fix #2: services/agent_service.py
- Adicionar inicialização `extra_data` em `create_agent()`
- Arquivo corrigido: `02_agent_service_FIXED.py`

```bash
cp 02_agent_service_FIXED.py backend/app/services/agent_service.py
```

### Fix #3: core/security/auth.py
- Implementar `get_current_tenant_id()` extraindo do JWT (sem query BD)
- Arquivo corrigido: `03_auth_FIXED.py`

```bash
cp 03_auth_FIXED.py backend/app/core/security/auth.py
```

---

## 📥 Passo 2: Criar Novos Arquivos Fase 5A

### 1. schemas/process.py
```bash
cp 04_process_schemas.py backend/app/schemas/process.py
```

**O que contém:**
- ProcessBase, ProcessCreate, ProcessRead, ProcessUpdate
- ProcessFilterParams (com filtros avançados: tags ANY/ALL, busca textual)
- VersaoBase, VersaoCreate, VersaoRead, VersaoReadFull
- ActivateVersionRequest/Response

### 2. services/process_service.py
```bash
cp 05_process_service.py backend/app/services/process_service.py
```

**O que contém:**
- `ProcessService` com 11 métodos:
  - `list_processes()` - paginado + filtros
  - `create_process()` - com validação de duplicação
  - `get_process()` - por ID
  - `update_process()` - com validação
  - `delete_process()` - soft delete
  - `list_versions()` - todas as versões
  - `create_version()` - com validação de semver
  - `get_version()` - por ID
  - `activate_version()` - transação atômica
  - `get_total_versions()` - helper
  - `get_active_version()` - helper

### 3. api/v1/processes.py
```bash
cp 06_processes_endpoints.py backend/app/api/v1/processes.py
```

**O que contém:**
- 8 endpoints REST:
  - `GET /processes` - listagem com filtros
  - `GET /processes/{id}` - detalhe
  - `POST /processes` - criar
  - `PUT /processes/{id}` - atualizar
  - `DELETE /processes/{id}` - soft delete
  - `GET /processes/{id}/versions` - listar versões
  - `POST /processes/{id}/versions` - criar versão
  - `PUT /processes/{id}/versions/{vid}/activate` - ativar versão

### 4. Atualizar schemas/__init__.py
```bash
cp 07_api_v1_init.py backend/app/api/v1/__init__.py
```

---

## ✅ Passo 3: Atualizar Imports

### backend/app/schemas/__init__.py

Adicionar no final:
```python
# Processo (Fase 5A)
from .process import (
    ProcessBase,
    ProcessCreate,
    ProcessRead,
    ProcessUpdate,
    ProcessFilterParams,
    VersaoBase,
    VersaoCreate,
    VersaoRead,
    VersaoReadFull,
    ActivateVersionRequest,
    ActivateVersionResponse,
    ProcessReadWithVersion,
)

__all__ = [
    # ... (existente)
    
    # Processo
    "ProcessBase",
    "ProcessCreate",
    "ProcessRead",
    "ProcessUpdate",
    "ProcessFilterParams",
    "VersaoBase",
    "VersaoCreate",
    "VersaoRead",
    "VersaoReadFull",
    "ActivateVersionRequest",
    "ActivateVersionResponse",
    "ProcessReadWithVersion",
]
```

---

## 🗄️ Passo 4: Validar Modelos

Seus modelos já existem em `backend/app/models/core.py`:
- ✅ `Processo` (table=True)
- ✅ `VersaoProcesso` (table=True)
- ✅ Relacionamento Processo → VersaoProcesso

**Verificar se:**
```python
# Em core.py, deve existir:
class Processo(BaseModel, table=True):
    # ... com related
    versoes: List["VersaoProcesso"] = Relationship(...)

class VersaoProcesso(BaseModel, table=True):
    # ... com related
    processo: Processo = Relationship(...)
```

Se falta algo, use seu arquivo de modelos existente.

---

## 🧪 Passo 5: Testar

### 5.1 Rodar a API
```bash
cd backend
uvicorn app.main:app --reload
```

### 5.2 Executar testes cURL
```bash
# Copiar script de testes
cp 08_test_fase5a_curl.sh backend/scripts/

# Tornar executável
chmod +x backend/scripts/test_fase5a_curl.sh

# Você precisa do seu ACCESS_TOKEN primeiro
# 1. Fazer login para obter token
# 2. Atualizar variável ACCESS_TOKEN no script
# 3. Executar

./backend/scripts/test_fase5a_curl.sh
```

### 5.3 Testar no Swagger UI
```
http://localhost:8000/docs

# Navegar até a seção "Processos"
# Testar cada endpoint diretamente
```

### 5.4 Verificar no Banco (psql)
```sql
-- Conectar ao PostgreSQL
psql -U user -d botmanager

-- Listar processos
SELECT id, name, tipo, is_active, created_at FROM processo;

-- Listar versões
SELECT id, processo_id, version, is_active, created_at FROM versao_processo;

-- Verificar relação
SELECT p.name, v.version, v.is_active 
FROM processo p 
LEFT JOIN versao_processo v ON p.id = v.processo_id
ORDER BY p.created_at DESC;
```

---

## 📊 Fluxo de Dados Esperado

### Criar Processo:
```
POST /processes
{
  "name": "invoice_processing",
  "tipo": "unattended",
  "tags": ["financeiro"]
}
↓
ProcessCreate schema validação
↓
ProcessService.create_process()
↓
INSERT INTO processo (id, tenant_id, name, tipo, tags, is_active, created_at, deleted_at)
↓
ProcessRead response
{
  "id": "uuid-123",
  "name": "invoice_processing",
  "total_versions": 0,
  "active_version": null
}
```

### Criar Versão:
```
POST /processes/{id}/versions
{
  "version": "1.0.0",
  "package_path": "s3://bucket/v1.0.0.zip"
}
↓
VersaoCreate schema validação
↓
ProcessService.create_version()
  - Validar versão semântica
  - Validar versão não duplica
↓
INSERT INTO versao_processo (id, processo_id, version, is_active, created_at)
↓
VersaoRead response
{
  "id": "uuid-456",
  "version": "1.0.0",
  "is_active": false
}
```

### Ativar Versão:
```
PUT /processes/{id}/versions/{vid}/activate
{}
↓
ProcessService.activate_version()
  - BEGIN NESTED TRANSACTION
  - UPDATE versao_processo SET is_active=false WHERE processo_id={id} AND is_active=true
  - UPDATE versao_processo SET is_active=true WHERE id={vid}
  - COMMIT
↓
UPDATE processo SET updated_at=now()
↓
ActivateVersionResponse
{
  "version": "1.0.0",
  "is_active": true
}
```

---

## 🐛 Troubleshooting

### Erro: ImportError - process module not found
**Solução:** Certificar que `backend/app/api/v1/processes.py` foi criado

### Erro: ConflictError - Nome já existe
**Esperado:** Você está tentando criar 2 processos com mesmo nome no mesmo tenant

### Erro: ValidationError - Versão inválida
**Solução:** Versão deve ser `X.Y.Z` (ex: 1.0.0, 2.1.5)

### Erro: NotFoundError - Processo não encontrado
**Solução:** Verificar que processo_id é válido e pertence ao seu tenant

### Erro: 401 Unauthorized
**Solução:** ACCESS_TOKEN expirado ou inválido - fazer login novamente

### Erro: Soft deleted not showing
**Esperado:** Queries automáticamente filtram `deleted_at IS NULL`

---

## ✅ Checklist de Integração

```
□ [1] Copiar agent.py (FIX #1)
□ [2] Copiar agent_service.py (FIX #2)
□ [3] Copiar auth.py em core/security/ (FIX #3)
□ [4] Copiar process.py em schemas/
□ [5] Copiar process_service.py em services/
□ [6] Copiar processes.py em api/v1/
□ [7] Copiar __init__.py em api/v1/
□ [8] Atualizar schemas/__init__.py (adicionar imports)
□ [9] Validar modelos Processo e VersaoProcesso
□ [10] Rodar API: uvicorn app.main:app --reload
□ [11] Testar no Swagger: http://localhost:8000/docs
□ [12] Executar testes cURL (com token válido)
□ [13] Verificar dados no PostgreSQL
□ [14] Revisar logs da API
□ [15] Pronto para Produção!
```

---

## 📚 Próximas Fases

Após Fase 5A, foco em:

**Fase 5B: Execuções**
- CRUD de execuções
- Heartbeat de agentes
- Filas de itens

**Fase 5C: Governança**
- Assets (variáveis globais)
- Credenciais (criptografadas)
- Agendamentos (cron)

**Fase 6: Monitoramento**
- Auditoria de eventos
- Logs estruturados
- Dashboards

---

## 🎯 Resumo Fase 5A

✅ **3 Fixes aplicados:**
- FIX #1: metadata → extra_data (padronização)
- FIX #2: tenant_id no service (com extra_data inicializado)
- FIX #3: get_current_tenant_id() do JWT (sem query BD)

✅ **Fase 5A Completa:**
- ✅ 5 arquivos novos (schemas, service, endpoints, init, testes)
- ✅ 8 endpoints REST (CRUD processo + versões)
- ✅ Transação atômica de ativação de versão
- ✅ Filtros avançados (tags ANY/ALL, busca textual)
- ✅ Soft delete com preservation de versões
- ✅ Multi-tenant seguro
- ✅ Script cURL para testes

**Status: 🚀 PRONTO PARA INTEGRAR**

---

## 📞 Dúvidas?

Se algo não ficar claro:
1. Revisar os comentários nos arquivos
2. Consultar os testes cURL para ver payload/response esperado
3. Verificar logs da API para erros específicos
4. Consultar modelo em `backend/app/models/core.py`

**Boa sorte! 🎉**