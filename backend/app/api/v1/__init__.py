# backend/app/api/v1/__init__.py
"""
API v1 - Routers e endpoints versionados.

Suporta:
- Health checks
- Autenticação (login, register, refresh) ✅ ADICIONADO
- Agentes (CRUD + heartbeat)
- Processos (CRUD + versões)
"""
from fastapi import APIRouter
from app.api.v1 import health, auth, agents, processes  # ✅ Adicionar auth


# Router principal da v1
api_router = APIRouter()

# Registra sub-routers (ORDEM IMPORTA!)
api_router.include_router(health.router)
api_router.include_router(auth.router)      # ✅ Registrar auth AQUI
api_router.include_router(agents.router)
api_router.include_router(processes.router)

# TODO: Adicionar outros routers conforme desenvolvidos
# api_router.include_router(executions.router)
# api_router.include_router(queues.router)
# etc.


__all__ = ["api_router"]