# backend/app/api/v1/governance.py
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, status, Query

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.core.security import get_current_tenant_id
from app.schemas.common import PaginatedResponse
from app.schemas.governance import (
    AssetCreate, AssetRead, AssetUpdate, AssetFilterParams,
    CredencialCreate, CredencialRead
)
from app.services.governance_service import GovernanceService

router = APIRouter(tags=["Governança"])

# ================= ASSETS =================

@router.post("/assets", response_model=AssetRead, status_code=status.HTTP_201_CREATED)
async def create_asset(
    data: AssetCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session)
):
    service = GovernanceService(session)
    return await service.create_asset(tenant_id, data)

@router.get("/assets", response_model=List[AssetRead]) # Simplificado para lista direta ou use PaginatedResponse
async def list_assets(
    params: AssetFilterParams = Depends(),
    tenant_id: UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session)
):
    service = GovernanceService(session)
    return await service.list_assets(tenant_id, params)

# ================= CREDENCIAIS =================

@router.post("/credentials", response_model=CredencialRead, status_code=status.HTTP_201_CREATED)
async def create_credential(
    data: CredencialCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session)
):
    """
    Cria uma nova credencial. A senha enviada será encriptada (AES-256) antes de salvar.
    """
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