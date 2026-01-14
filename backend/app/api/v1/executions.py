# backend/app/api/v1/executions.py
"""
Endpoints REST para controle e monitoramento de Execuções RPA.

Rotas:
- GET  /executions            → Listar histórico (filtros por status, processo, agente)
- POST /executions/trigger    → Iniciar nova execução (Manual/Ad-hoc)
- GET  /executions/{id}       → Detalhes e logs da execução
- POST /executions/{id}/stop  → Solicitar interrupção
"""

from uuid import UUID
from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import get_current_tenant_id
from app.core.logging import get_logger
from app.schemas.execution import (
    ExecutionCreate,
    ExecutionRead,
    ExecutionFilterParams,
    ExecutionSummary,
    ExecutionActionResponse
)
from app.schemas.common import PaginatedResponse
from app.services.execution_service import ExecutionService

logger = get_logger(__name__)

router = APIRouter(prefix="/executions", tags=["Execuções"])

@router.get(
    "",
    response_model=PaginatedResponse[ExecutionRead],
    summary="Listar Execuções",
    description="Retorna o histórico de execuções com filtros avançados."
)
async def list_executions(
    params: ExecutionFilterParams = Depends(),
    tenant_id: UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session)
):
    service = ExecutionService(session)
    return await service.list_executions(tenant_id, params)

@router.post(
    "/trigger",
    response_model=ExecutionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Disparar Processo",
    description="Cria uma nova entrada na fila de execução para um robô processar."
)
async def trigger_execution(
    data: ExecutionCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session)
):
    """
    Inicia uma execução manual. 
    O serviço validará se o processo tem uma versão ativa antes de criar.
    """
    service = ExecutionService(session)
    execution = await service.trigger_manual_execution(tenant_id, data)
    
    logger.info(f"Execution {execution.id} triggered for process {data.processo_id}")
    return execution

@router.get(
    "/{execution_id}",
    response_model=ExecutionRead,
    summary="Detalhes da Execução",
)
async def get_execution(
    execution_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session)
):
    service = ExecutionService(session)
    return await service.get_execution_by_id(tenant_id, execution_id)

@router.post(
    "/{execution_id}/stop",
    response_model=ExecutionActionResponse,
    summary="Interromper Execução",
    description="Solicita a parada forçada de uma execução em andamento."
)
async def stop_execution(
    execution_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session)
):
    service = ExecutionService(session)
    success = await service.request_stop(tenant_id, execution_id)
    
    return ExecutionActionResponse(
        success=success,
        message="Solicitação de interrupção enviada ao agente" if success else "Não foi possível interromper"
    )

@router.get(
    "/stats/summary",
    response_model=ExecutionSummary,
    summary="Sumário de Execuções",
    description="Retorna contagem de sucessos/falhas para dashboards."
)
async def get_execution_summary(
    days: int = Query(7, ge=1, le=30),
    tenant_id: UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session)
):
    service = ExecutionService(session)
    return await service.get_summary_stats(tenant_id, days)

from app.schemas.execution import ExecutionUpdate # Certifique-se que importa isto

@router.patch(
    "/{execution_id}",
    response_model=ExecutionRead,
    summary="Atualizar Estado da Execução",
    description="Usado pelo Robô para reportar progresso, sucesso ou falha."
)
async def update_execution_status(
    execution_id: UUID,
    update_data: ExecutionUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session)
):
    service = ExecutionService(session)
    return await service.update_execution_status(tenant_id, execution_id, update_data)