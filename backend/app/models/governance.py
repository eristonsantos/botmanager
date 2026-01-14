import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from enum import Enum
from sqlmodel import Field, SQLModel, Column, Enum as SQLAlchemyEnum, Relationship

# IMPORTANTE: Importamos SoftDeleteMixin para adicionar 'deleted_at'
from app.models.base import BaseModel, SoftDeleteMixin 

if TYPE_CHECKING:
    from app.models.core import Processo 

# --- ENUMS ---
class TipoAssetEnum(str, Enum):
    text = "text"
    integer = "integer"
    boolean = "boolean"
    json = "json"

class TipoCredencialEnum(str, Enum):
    basic_auth = "basic_auth"
    token = "token"
    certificate = "certificate"

class ScopeAssetEnum(str, Enum):
    global_ = "global"
    process = "process"
    robot = "robot"

# --- MODELOS ---

# 1. Asset (Adicionado SoftDeleteMixin)
class Asset(BaseModel, SoftDeleteMixin, table=True): 
    __tablename__ = "asset"
    
    name: str = Field(index=True)
    value: str
    description: Optional[str] = None
    
    tipo: TipoAssetEnum = Field(
        sa_column=Column(SQLAlchemyEnum(TipoAssetEnum))
    )
    
    scope: str = Field(default="global")
    
    # Relação com Processo
    process_id: Optional[uuid.UUID] = Field(default=None, foreign_key="processo.id", nullable=True)
    processo: Optional["Processo"] = Relationship(back_populates="assets")

# 2. Credencial (Adicionado SoftDeleteMixin)
class Credencial(BaseModel, SoftDeleteMixin, table=True):
    __tablename__ = "credencial"
    
    name: str = Field(index=True)
    username: Optional[str] = None
    encrypted_password: str
    description: Optional[str] = None
    last_rotated: datetime = Field(default_factory=datetime.utcnow)

# 3. Agendamento (Mantido igual - NÃO altere para não quebrar o Scheduler)
class Agendamento(BaseModel, table=True):
    __tablename__ = "agendamento"
    
    name: str
    cron_expression: str
    is_active: bool = Field(default=True)
    
    process_id: Optional[uuid.UUID] = Field(default=None, foreign_key="processo.id")
    processo: Optional["Processo"] = Relationship(back_populates="agendamentos")
    
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None