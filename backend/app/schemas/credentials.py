# backend/app/schemas/credentials.py
from typing import Optional
from uuid import UUID
from pydantic import Field

from .common import BaseSchema, TimestampMixin, TenantMixin

class CredentialBase(BaseSchema):
    name: str = Field(..., min_length=1, max_length=100, examples=["SAP_PRODUCAO"])
    description: Optional[str] = None
    credential_type: str = Field(default="password", description="password, token, certificate")

class CredentialCreate(CredentialBase):
    """Payload para criar uma nova credencial (senha vem em texto plano aqui)."""
    value: str = Field(..., min_length=1, description="A senha ou token real")

class CredentialRead(CredentialBase, TimestampMixin, TenantMixin):
    """Leitura segura (NÃO expõe a senha)."""
    id: UUID
    is_active: bool

class CredentialRevealed(CredentialRead):
    """Leitura insegura (para o Robô) - Expõe a senha."""
    value: str # A senha descriptografada