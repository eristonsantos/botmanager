from datetime import datetime
from uuid import UUID
from sqlmodel import Field
from typing import Optional

from .base import BaseModel

class Credential(BaseModel, table=True):
    __tablename__ = "credential"

    tenant_id: UUID = Field(foreign_key="tenant.id", index=True)
    
    name: str = Field(index=True, max_length=100) # Ex: "SAP_PRODUCAO"
    description: Optional[str] = Field(default=None)
    
    # O valor real criptografado (Ex: gAAAAABk...)
    encrypted_value: str = Field(..., description="Valor criptografado da credencial")
    
    # Metadata
    credential_type: str = Field(default="password") # password, token, certificate
    is_active: bool = Field(default=True)