# backend/app/models/workload.py
from datetime import datetime
from enum import Enum
from typing import Optional, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Column, JSON, String, Index, Text, DateTime
from sqlmodel import Field, Relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .core import Processo, Agente, Execucao

# ==================== ENUMS ====================

class PriorityEnum(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

class StatusItemFilaEnum(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"
    DEFERRED = "deferred"

# ESTE É O QUE ESTÁ FALTANDO:
class TipoExcecaoEnum(str, Enum):
    BUSINESS = "business"  # Erro de regra de negócio (não retenta)
    SYSTEM = "system"      # Erro de sistema/infra (permite retenta)

class SeverityEnum(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

# ==================== MODELOS ====================

class ItemFila(BaseModel, table=True):
    __tablename__ = "item_fila"

    queue_name: str = Field(index=True, max_length=100)
    status: StatusItemFilaEnum = Field(default=StatusItemFilaEnum.PENDING)
    priority: PriorityEnum = Field(default=PriorityEnum.NORMAL)
    
    payload: dict = Field(default_factory=dict, sa_column=Column(JSON))
    reference: Optional[str] = Field(default=None, index=True)
    
    retry_count: int = Field(default=0)
    max_retries: int = Field(default=3)
    deferred_until: Optional[datetime] = Field(default=None)
    
    locked_by: Optional[UUID] = Field(default=None, foreign_key="agente.id")
    locked_until: Optional[datetime] = Field(default=None)

    processo_id: UUID = Field(foreign_key="processo.id", index=True)
    execucao_id: Optional[UUID] = Field(default=None, foreign_key="execucao.id")

class Excecao(BaseModel, table=True):
    __tablename__ = "excecao"

    tipo: TipoExcecaoEnum = Field(default=TipoExcecaoEnum.SYSTEM)
    severity: SeverityEnum = Field(default=SeverityEnum.MEDIUM)
    message: str = Field(sa_column=Column(Text))
    stack_trace: Optional[str] = Field(default=None, sa_column=Column(Text))
    
    execucao_id: UUID = Field(foreign_key="execucao.id", index=True)
    item_fila_id: Optional[UUID] = Field(default=None, foreign_key="item_fila.id")