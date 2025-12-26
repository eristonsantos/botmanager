# backend/app/schemas/governance.py
from datetime import datetime
from typing import Optional, Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.governance import TipoAssetEnum, ScopeAssetEnum, TipoCredencialEnum
from app.schemas.common import PaginationParams

# ================= ASSETS =================

class AssetBase(BaseModel):
    name: str = Field(..., max_length=100)
    tipo: TipoAssetEnum
    value: str  # O frontend deve enviar stringificado
    description: Optional[str] = Field(None, max_length=500)
    scope: ScopeAssetEnum = ScopeAssetEnum.GLOBAL
    scope_id: Optional[UUID] = None

class AssetCreate(AssetBase):
    pass

class AssetUpdate(BaseModel):
    value: Optional[str] = None
    description: Optional[str] = None
    # Geralmente não se muda o tipo ou escopo após criar para evitar quebra de contratos

class AssetRead(AssetBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class AssetFilterParams(PaginationParams):
    name: Optional[str] = None
    scope: Optional[ScopeAssetEnum] = None
    processo_id: Optional[UUID] = None

# ================= CREDENCIAIS =================

class CredencialBase(BaseModel):
    name: str = Field(..., max_length=100)
    tipo: TipoCredencialEnum
    username: Optional[str] = Field(None, max_length=255)
    extra_data: dict = Field(default_factory=dict)
    rotation_days: Optional[int] = None

class CredencialCreate(CredencialBase):
    password: str = Field(..., description="Senha em texto plano (será encriptada)")

class CredencialUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = Field(None, description="Nova senha para rotação")
    extra_data: Optional[dict] = None
    is_active: Optional[bool] = None

class CredencialRead(CredencialBase):
    id: UUID
    tenant_id: UUID
    expires_at: Optional[datetime]
    last_rotated: Optional[datetime]
    # NOTE: NUNCA retornamos encrypted_password aqui
    
    class Config:
        from_attributes = True