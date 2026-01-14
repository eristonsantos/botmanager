# backend/app/api/v1/governance.py
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, status, Query, HTTPException
from sqlalchemy import select 
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from croniter import croniter

from app.core.database import get_session
from app.core.security import get_current_tenant_id
from app.schemas.common import PaginatedResponse
from app.schemas.governance import (
    AssetCreate, AssetRead, AssetUpdate, AssetFilterParams,
    CredencialCreate, CredencialRead, CredencialRevealed,
    AgendamentoCreate, AgendamentoRead, AgendamentoUpdate
)
from app.models.governance import Asset, Credencial,Agendamento
from app.services.governance_service import GovernanceService

router = APIRouter(prefix="/governance", tags=["Governança"])

# ================= ASSETS =================

@router.post("/assets", response_model=AssetRead, status_code=status.HTTP_201_CREATED)
async def create_asset(
    data: AssetCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session)
):
    service = GovernanceService(session)
    return await service.create_asset(tenant_id, data)

@router.get("/assets", response_model=List[AssetRead]) 
async def list_assets(
    params: AssetFilterParams = Depends(),
    tenant_id: UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session)
):
    service = GovernanceService(session)
    return await service.list_assets(tenant_id, params)

# --- ROTA DE DELETE QUE FALTAVA ---
@router.delete("/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    asset_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session)
):
    service = GovernanceService(session)
    await service.delete_asset(tenant_id, asset_id)
    return None

# ================= CREDENCIAIS =================

@router.post("/credentials", response_model=CredencialRead, status_code=status.HTTP_201_CREATED)
async def create_credential(
    data: CredencialCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session)
):
    service = GovernanceService(session)
    return await service.create_credential(tenant_id, data)

@router.get("/credentials", response_model=List[CredencialRead])
async def list_credentials(
    skip: int = 0,
    limit: int = 50,
    tenant_id: UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session)
):
    service = GovernanceService(session)
    return await service.list_credentials(tenant_id, skip, limit)

@router.get("/credentials/{name}/reveal", response_model=CredencialRevealed)
async def get_decrypted_credential(
    name: str,
    tenant_id: UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session)
):
    service = GovernanceService(session)
    cred = await service.get_by_name(tenant_id, name, reveal=True)
    if not cred:
        raise HTTPException(status_code=404, detail=f"Credencial '{name}' não encontrada.")
    return cred

# --- ROTA DE DELETE QUE FALTAVA ---
@router.delete("/credentials/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_credential(
    credential_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session)
):
    service = GovernanceService(session)
    await service.delete_credential(tenant_id, credential_id)
    return None


# ================= AGENDAMENTOS (TRIGGERS) =================
@router.post("/schedules", response_model=AgendamentoRead, status_code=status.HTTP_201_CREATED)
@router.post("/schedules", response_model=AgendamentoRead, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    data: AgendamentoCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session)
):
    # 1. Cria o objeto
    agendamento = Agendamento(**data.model_dump(), tenant_id=tenant_id)
    
    # 2. CALCULA A PRÓXIMA EXECUÇÃO (Correção)
    try:
        # Calcula a próxima data a partir de AGORA
        iter = croniter(data.cron_expression, datetime.now())
        agendamento.next_run = iter.get_next(datetime)
    except Exception as e:
        # Se o CRON for inválido, podemos deixar null ou dar erro
        print(f"Erro ao calcular CRON: {e}")
        # Opcional: raise HTTPException(400, "CRON Inválido")

    session.add(agendamento)
    await session.commit()
    await session.refresh(agendamento)
    return agendamento

@router.get("/schedules", response_model=List[AgendamentoRead])
async def list_schedules(
    tenant_id: UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session)
):
    query = select(Agendamento).where(Agendamento.tenant_id == tenant_id)
    result = await session.execute(query)
    return result.scalars().all()

@router.delete("/schedules/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session)
):
    query = select(Agendamento).where(Agendamento.id == id, Agendamento.tenant_id == tenant_id)
    item = (await session.execute(query)).scalar_one_or_none()
    if item:
        await session.delete(item)
        await session.commit()

@router.patch("/schedules/{id}", response_model=AgendamentoRead)
async def update_schedule(
    id: UUID,
    data: AgendamentoUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session)
):
    query = select(Agendamento).where(Agendamento.id == id, Agendamento.tenant_id == tenant_id)
    item = (await session.execute(query)).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)
    
    # Recalcula next_run se cron_expression foi atualizado
    if "cron_expression" in update_data:
        try:
            iter = croniter(item.cron_expression, datetime.now())
            item.next_run = iter.get_next(datetime)
        except Exception as e:
            print(f"Erro ao calcular CRON: {e}")
        
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item