# backend/app/api/v1/credentials.py
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import get_current_tenant_id
from app.schemas.credentials import CredentialCreate, CredentialRead, CredentialRevealed
from app.services.credential_service import CredentialService

router = APIRouter(prefix="/credentials", tags=["Credentials (Vault)"])

@router.post("", response_model=CredentialRead, status_code=status.HTTP_201_CREATED)
async def create_credential(
    data: CredentialCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session)
):
    """Cria uma nova credencial segura."""
    service = CredentialService(session)
    return await service.create(tenant_id, data)

@router.get("", response_model=List[CredentialRead])
async def list_credentials(
    tenant_id: UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session)
):
    """Lista credenciais (sem mostrar as senhas)."""
    service = CredentialService(session)
    return await service.list(tenant_id)

@router.get("/{name}/reveal", response_model=CredentialRevealed)
async def get_decrypted_credential(
    name: str,
    tenant_id: UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session)
):
    """
    USO EXCLUSIVO DO ROBÔ: Retorna a credencial com a senha revelada.
    """
    service = CredentialService(session)
    cred = await service.get_by_name(tenant_id, name, reveal=True)
    
    if not cred:
        raise HTTPException(status_code=404, detail="Credencial não encontrada")
    
    return cred