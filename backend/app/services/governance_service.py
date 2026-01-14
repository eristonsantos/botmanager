# backend/app/services/governance_service.py
from typing import List, Optional, Any
from uuid import UUID
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, col

from app.core.exceptions import NotFoundError, ConflictError
from app.core.security.encryption import encrypt_credential, decrypt_credential
from app.models.governance import Asset, Credencial, TipoAssetEnum
from app.schemas.governance import AssetCreate, AssetFilterParams, CredencialCreate

class GovernanceService:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ================= ASSETS =================
    async def create_asset(self, tenant_id: UUID, data: AssetCreate) -> Asset:
        stmt = select(Asset).where(Asset.name == data.name, Asset.tenant_id == tenant_id)
        if (await self.session.execute(stmt)).scalar_one_or_none():
            raise ConflictError(f"Asset '{data.name}' já existe.")

        asset = Asset(**data.model_dump(), tenant_id=tenant_id)
        self.session.add(asset)
        await self.session.commit()
        await self.session.refresh(asset)
        return asset

    async def list_assets(self, tenant_id: UUID, params: AssetFilterParams) -> List[Asset]:
        query = select(Asset).where(Asset.tenant_id == tenant_id)
        if params.name:
            query = query.where(col(Asset.name).icontains(params.name))
        query = query.offset(params.skip).limit(params.limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def delete_asset(self, tenant_id: UUID, asset_id: UUID) -> None:
        stmt = select(Asset).where(Asset.id == asset_id, Asset.tenant_id == tenant_id)
        asset = (await self.session.execute(stmt)).scalar_one_or_none()
        if not asset:
            raise NotFoundError(resource="Asset", identifier=str(asset_id))
        await self.session.delete(asset)
        await self.session.commit()

    # ================= CREDENCIAIS =================
    async def create_credential(self, tenant_id: UUID, data: CredencialCreate) -> Credencial:
        stmt = select(Credencial).where(Credencial.name == data.name, Credencial.tenant_id == tenant_id)
        if (await self.session.execute(stmt)).scalar_one_or_none():
            raise ConflictError(f"Credencial '{data.name}' já existe.")

        encrypted = encrypt_credential(data.password)
        cred_data = data.model_dump(exclude={"password"})
        
        # --- CORREÇÃO: DATA SEM TIMEZONE (NAIVE) ---
        credencial = Credencial(
            **cred_data,
            encrypted_password=encrypted,
            tenant_id=tenant_id,
            last_rotated=datetime.utcnow() 
        )
        
        self.session.add(credencial)
        await self.session.commit()
        await self.session.refresh(credencial)
        return credencial

    async def list_credentials(self, tenant_id: UUID, skip: int = 0, limit: int = 50) -> List[Credencial]:
        query = select(Credencial).where(Credencial.tenant_id == tenant_id).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def delete_credential(self, tenant_id: UUID, credential_id: UUID) -> None:
        stmt = select(Credencial).where(Credencial.id == credential_id, Credencial.tenant_id == tenant_id)
        cred = (await self.session.execute(stmt)).scalar_one_or_none()
        if not cred:
            raise NotFoundError(resource="Credencial", identifier=str(credential_id))
        await self.session.delete(cred)
        await self.session.commit()

    async def get_by_name(self, tenant_id: UUID, name: str, reveal: bool = False):
        stmt = select(Credencial).where(Credencial.name == name, Credencial.tenant_id == tenant_id)
        cred = (await self.session.execute(stmt)).scalar_one_or_none()
        if not cred: return None
        if reveal:
            decrypted = decrypt_credential(cred.encrypted_password)
            return {**cred.model_dump(), "value": decrypted}
        return cred