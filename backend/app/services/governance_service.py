# backend/app/services/governance_service.py
from typing import List, Optional, Any
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, col

from app.core.exceptions import NotFoundError, ConflictError
from app.core.security.encryption import encrypt_credential, decrypt_credential
from app.models.governance import Asset, Credencial, TipoAssetEnum
from app.schemas.governance import (
    AssetCreate, AssetUpdate, AssetFilterParams,
    CredencialCreate, CredencialUpdate
)

class GovernanceService:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ================= ASSETS =================
    
    async def create_asset(self, tenant_id: UUID, data: AssetCreate) -> Asset:
        # Verificar duplicidade
        stmt = select(Asset).where(
            Asset.name == data.name,
            Asset.tenant_id == tenant_id
        )
        existing = await self.session.execute(stmt)
        if existing.scalar_one_or_none():
            raise ConflictError(f"Asset '{data.name}' já existe.")

        asset = Asset(**data.model_dump(), tenant_id=tenant_id)
        self.session.add(asset)
        await self.session.commit()
        await self.session.refresh(asset)
        return asset

    async def get_asset_value(self, tenant_id: UUID, name: str) -> Any:
        """
        Método helper para retornar o valor tipado (int, bool, json) 
        ao invés da string bruta. Útil para execução de robôs.
        """
        stmt = select(Asset).where(
            Asset.name == name,
            Asset.tenant_id == tenant_id
        )
        res = await self.session.execute(stmt)
        asset = res.scalar_one_or_none()
        
        if not asset:
            raise NotFoundError(resource="Asset", identifier=name)
            
        # Conversão de Tipos
        if asset.tipo == TipoAssetEnum.INTEGER:
            return int(asset.value)
        elif asset.tipo == TipoAssetEnum.BOOLEAN:
            return asset.value.lower() == "true"
        elif asset.tipo == TipoAssetEnum.JSON:
            import json
            return json.loads(asset.value)
        
        return asset.value

    async def list_assets(self, tenant_id: UUID, params: AssetFilterParams) -> List[Asset]:
        query = select(Asset).where(Asset.tenant_id == tenant_id)
        
        if params.name:
            query = query.where(col(Asset.name).icontains(params.name))
        if params.scope:
            query = query.where(Asset.scope == params.scope)
            
        # Paginação simples
        query = query.offset(params.skip).limit(params.limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    # ================= CREDENCIAIS =================

    async def create_credential(self, tenant_id: UUID, data: CredencialCreate) -> Credencial:
        # Verificar duplicidade
        stmt = select(Credencial).where(
            Credencial.name == data.name,
            Credencial.tenant_id == tenant_id
        )
        if (await self.session.execute(stmt)).scalar_one_or_none():
            raise ConflictError(f"Credencial '{data.name}' já existe.")

        # Criptografia
        encrypted = encrypt_credential(data.password)
        
        cred_data = data.model_dump(exclude={"password"})
        credencial = Credencial(
            **cred_data,
            encrypted_password=encrypted,
            tenant_id=tenant_id,
            last_rotated=datetime.now(timezone.utc)
        )
        
        self.session.add(credencial)
        await self.session.commit()
        await self.session.refresh(credencial)
        return credencial

    async def get_decrypted_credential_value(self, tenant_id: UUID, credential_id: UUID) -> str:
        """
        Retorna a senha em texto plano. 
        ⚠️ PERIGOSO: Usar apenas internamente (Robôs) ou endpoint de 'reveal' auditado.
        """
        stmt = select(Credencial).where(
            Credencial.id == credential_id,
            Credencial.tenant_id == tenant_id
        )
        res = await self.session.execute(stmt)
        cred = res.scalar_one_or_none()
        
        if not cred:
            raise NotFoundError(resource="Credencial", identifier=credential_id)
            
        return decrypt_credential(cred.encrypted_password)

    async def list_credentials(self, tenant_id: UUID, skip: int = 0, limit: int = 50) -> List[Credencial]:
        query = select(Credencial).where(Credencial.tenant_id == tenant_id)
        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()