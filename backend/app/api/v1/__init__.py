# backend/app/api/v1/__init__.py
from fastapi import APIRouter

from app.api.v1 import auth, agents, health, workload, governance, processes

# Cria o router principal que agrupa os módulos base
api_router = APIRouter()

# Inclui os routers
api_router.include_router(auth.router)
api_router.include_router(agents.router)
api_router.include_router(health.router)
api_router.include_router(workload.router)
api_router.include_router(governance.router)
api_router.include_router(processes.router)