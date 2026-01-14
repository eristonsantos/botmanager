# backend/app/schemas/governance.py
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict

# Usando minúsculo para bater com o Model
class TipoAssetEnum(str, Enum):
    text = "text"
    integer = "integer"
    boolean = "boolean"
    json = "json"

# --- ASSETS ---

class AssetCreate(BaseModel):
    name: str
    value: str
    description: Optional[str] = None
    tipo: TipoAssetEnum = TipoAssetEnum.text
    scope: str = "global"

# --- ADICIONADO QUE FALTAVA ---
class AssetUpdate(BaseModel):
    value: Optional[str] = None
    description: Optional[str] = None
# ------------------------------

class AssetRead(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    value: str
    tipo: TipoAssetEnum
    description: Optional[str] = None
    scope: str
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class AssetFilterParams(BaseModel):
    name: Optional[str] = None
    skip: int = 0
    limit: int = 100

# --- CREDENCIAIS ---

class CredencialCreate(BaseModel):
    name: str
    password: str
    username: Optional[str] = None
    description: Optional[str] = None

# --- ADICIONADO QUE FALTAVA ---
class CredencialUpdate(BaseModel):
    password: Optional[str] = None
    username: Optional[str] = None
    description: Optional[str] = None
# ------------------------------

class CredencialRead(BaseModel):
    id: UUID
    name: str
    username: Optional[str] = None
    description: Optional[str] = None
    last_rotated: datetime
    
    model_config = ConfigDict(from_attributes=True)

class CredencialRevealed(CredencialRead):
    value: str


# --- AGENDAMENTOS (TRIGGERS) ---
class AgendamentoCreate(BaseModel):
    name: str
    cron_expression: str  # Ex: "0 8 * * *"
    process_id: Optional[UUID] = None
    is_active: bool = True

class AgendamentoUpdate(BaseModel):
    name: Optional[str] = None
    cron_expression: Optional[str] = None
    is_active: Optional[bool] = None

class AgendamentoRead(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    cron_expression: str
    process_id: Optional[UUID] = None
    is_active: bool
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)