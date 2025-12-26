# backend/app/api/v1/workload.py
from uuid import UUID
from fastapi import APIRouter, Depends, status, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import get_current_tenant_id
from app.schemas.workload import (
    ItemFilaRead, 
    WorkloadActionResponse, 
    ExcecaoCreate
)
# Nota: Assumindo que criaremos o WorkloadService a seguir
from app.services.workload_service import WorkloadService

router = APIRouter(prefix="/workload", tags=["Workload"])

@router.post(
    "/{queue_name}/get-next",
    response_model=ItemFilaRead,
    status_code=status.HTTP_200_OK,
    summary="Obter Próximo Item",
    description="Busca o próximo item pendente na fila, respeitando prioridade e aplicando lock."
)
async def get_next_item(
    queue_name: str,
    agent_id: UUID = Body(..., embed=True),
    tenant_id: UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session)
):
    service = WorkloadService(session)
    return await service.get_next_item(tenant_id, queue_name, agent_id)

@router.patch(
    "/items/{item_id}/complete",
    response_model=WorkloadActionResponse,
    summary="Concluir Item",
    description="Marca um item de fila como concluído com sucesso."
)
async def complete_item(
    item_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session)
):
    service = WorkloadService(session)
    await service.complete_item(tenant_id, item_id)
    return WorkloadActionResponse(
        success=True, 
        status_final="completed", 
        message="Item processado com sucesso."
    )

@router.post(
    "/items/{item_id}/fail",
    response_model=WorkloadActionResponse,
    summary="Reportar Falha",
    description="Registra uma exceção e decide se o item vai para Retry ou Failed."
)
async def fail_item(
    item_id: UUID,
    excecao: ExcecaoCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session)
):
    service = WorkloadService(session)
    status_final = await service.fail_item(tenant_id, item_id, excecao)
    return WorkloadActionResponse(
        success=True,
        status_final=status_final,
        message=f"Falha registrada. Item movido para: {status_final}"
    )