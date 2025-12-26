# backend/app/models/governance.py

from datetime import datetime
from enum import Enum
from typing import Optional, TYPE_CHECKING
from uuid import UUID

from sqlmodel import Field, Relationship, Column, String, JSON, Index, Text
from pydantic import field_validator

from .base import BaseModel
# Importar o Enum global de triggers
from .core import TriggerTypeEnum

if TYPE_CHECKING:
    from .core import Processo


# ==================== ENUMS ====================

class TipoAssetEnum(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    JSON = "json"
    ENCRYPTED = "encrypted"


class ScopeAssetEnum(str, Enum):
    GLOBAL = "global"      
    PROCESSO = "processo"  


class TipoCredencialEnum(str, Enum):
    BASIC_AUTH = "basic_auth"
    API_KEY = "api_key"
    OAUTH2 = "oauth2"
    CERTIFICATE = "certificate"
    CUSTOM = "custom"


# ==================== MODELOS ====================

class Asset(BaseModel, table=True):
    __tablename__ = "asset"
    
    name: str = Field(max_length=100, index=True)
    tipo: TipoAssetEnum = Field(default=TipoAssetEnum.STRING)
    
    # Usar Text para valores longos ou JSON strings
    value: str = Field(sa_column=Column(Text))
    
    description: Optional[str] = Field(default=None, max_length=500)
    
    scope: ScopeAssetEnum = Field(default=ScopeAssetEnum.GLOBAL, index=True)
    scope_id: Optional[UUID] = Field(default=None, foreign_key="processo.id", index=True)
    
    # Relacionamento
    processo: Optional["Processo"] = Relationship()
    
    @field_validator('scope_id')
    @classmethod # Em Pydantic V2/SQLModel é bom garantir @classmethod
    def validate_scope_id(cls, v, info):
        if info.data.get('scope') == ScopeAssetEnum.PROCESSO and not v:
            raise ValueError("scope_id é obrigatório quando o escopo é 'processo'")
        return v


class Credencial(BaseModel, table=True):
    __tablename__ = "credencial"
    
    name: str = Field(max_length=100, index=True)
    tipo: TipoCredencialEnum = Field(default=TipoCredencialEnum.BASIC_AUTH)
    
    username: Optional[str] = Field(default=None, max_length=255)
    encrypted_password: str = Field(sa_column=Column(Text)) # Senhas criptografadas podem ser longas
    
    extra_data: dict = Field(default_factory=dict, sa_column=Column(JSON))
    
    expires_at: Optional[datetime] = Field(default=None, index=True)
    last_rotated: Optional[datetime] = Field(default=None)
    rotation_days: Optional[int] = Field(default=None)


class Agendamento(BaseModel, table=True):
    __tablename__ = "agendamento"
    
    processo_id: UUID = Field(foreign_key="processo.id", index=True)
    name: str = Field(max_length=100)
    
    # Adicionado TriggerType para alinhar com o core
    trigger_type: TriggerTypeEnum = Field(default=TriggerTypeEnum.CRON)
    
    cron_expression: Optional[str] = Field(default=None, max_length=100)
    timezone: str = Field(default="UTC", max_length=50)
    
    is_active: bool = Field(default=True, index=True)
    input_data: dict = Field(default_factory=dict, sa_column=Column(JSON))
    
    last_run_at: Optional[datetime] = Field(default=None)
    next_run_at: Optional[datetime] = Field(default=None, index=True)
    
    # Relacionamento
    processo: "Processo" = Relationship()
    
    @field_validator('cron_expression')
    @classmethod
    def validate_cron_expression(cls, v, info):
        # Só valida se for do tipo CRON
        if info.data.get('trigger_type') == TriggerTypeEnum.CRON:
            from croniter import croniter
            if not v or not croniter.is_valid(v):
                raise ValueError(f"Expressão cron inválida: {v}")
        return v

# ==================== INDEXES ====================

Index('idx_asset_tenant_name', Asset.tenant_id, Asset.name, unique=True)
Index('idx_credencial_tenant_name', Credencial.tenant_id, Credencial.name, unique=True)
Index('idx_agendamento_tenant_active_next', Agendamento.tenant_id, Agendamento.is_active, Agendamento.next_run_at)