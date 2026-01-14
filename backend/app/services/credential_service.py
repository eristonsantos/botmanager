# backend/app/services/credential_service.py
import os
from uuid import UUID
from typing import Optional, List, Union, Dict, Any
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.credentials import Credential
from app.schemas.credentials import CredentialCreate
from app.core.exceptions import NotFoundError, AppException

class CredentialService:
    def __init__(self, session: AsyncSession):
        self.session = session
        
        # Carrega a chave do .env
        key = os.getenv("ENCRYPTION_KEY")
        if not key:
            raise AppException("ENCRYPTION_KEY não configurada no backend!")
        self.cipher = Fernet(key)

    def _encrypt(self, text: str) -> str:
        return self.cipher.encrypt(text.encode()).decode()

    def _decrypt(self, hash_text: str) -> str:
        return self.cipher.decrypt(hash_text.encode()).decode()

    async def create(self, tenant_id: UUID, data: CredentialCreate) -> Credential:
        encrypted_val = self._encrypt(data.value)
        credential = Credential(
            tenant_id=tenant_id,
            name=data.name,
            description=data.description,
            credential_type=data.credential_type,
            encrypted_value=encrypted_val
        )
        self.session.add(credential)
        await self.session.commit()
        await self.session.refresh(credential)
        return credential

    async def get_by_name(self, tenant_id: UUID, name: str, reveal: bool = False) -> Union[Credential, Dict[str, Any], None]:
        stmt = select(Credential).where(
            Credential.tenant_id == tenant_id,
            Credential.name == name,
            Credential.is_active == True
        )
        result = await self.session.execute(stmt)
        cred = result.scalar_one_or_none()
        
        if not cred:
            return None
        
        # --- CORREÇÃO AQUI ---
        if reveal:
            # Não podemos adicionar .value no objeto 'cred' direto.
            # Criamos um dicionário manual com os dados + o valor revelado.
            return {
                "id": cred.id,
                "tenant_id": cred.tenant_id,
                "name": cred.name,
                "description": cred.description,
                "credential_type": cred.credential_type,
                "is_active": cred.is_active,
                "created_at": cred.created_at,
                "updated_at": cred.updated_at,
                "value": self._decrypt(cred.encrypted_value) # <--- AQUI ESTÁ A SENHA
            }
            
        return cred

    async def list(self, tenant_id: UUID) -> List[Credential]:
        stmt = select(Credential).where(Credential.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()