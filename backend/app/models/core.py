# backend/app/models/core.py
from datetime import datetime
from enum import Enum
from typing import Optional, List, TYPE_CHECKING
from uuid import UUID
from sqlalchemy import Column, String, JSON, Index, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .workload import ItemFila, Excecao
    from .governance import Asset, Agendamento
    from .monitoring import LogExecucao

# --- ENUMS ---
class StatusAgenteEnum(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    MAINTENANCE = "maintenance"

class TipoProcessoEnum(str, Enum):
    ATTENDED = "attended"
    UNATTENDED = "unattended"
    HYBRID = "hybrid"

class StatusExecucaoEnum(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TriggerTypeEnum(str, Enum):
    CRON = "cron"           # Execução via expressão cron
    INTERVAL = "interval"   # Execução a cada X minutos/horas
    ONCE = "once"           # Execução única agendada
    MANUAL = "manual"       # Disparo manual via API/Dashboard

# --- MODELOS ---

class Agente(BaseModel, table=True):
    __tablename__ = "agente"
    
    name: str = Field(sa_column=Column(String(100), nullable=False))
    machine_name: str = Field(max_length=100)
    ip_address: Optional[str] = Field(default=None, max_length=45)
    status: StatusAgenteEnum = Field(default=StatusAgenteEnum.OFFLINE)
    version: Optional[str] = Field(default=None, max_length=20)
    last_heartbeat: Optional[datetime] = Field(default=None)
    extra_data: dict = Field(default_factory=dict, sa_column=Column(JSONB))

class Processo(BaseModel, table=True):
    __tablename__ = "processo"
    
    name: str = Field(sa_column=Column(String(100), nullable=False))
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    tipo: TipoProcessoEnum = Field(default=TipoProcessoEnum.UNATTENDED)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list, sa_column=Column(JSONB))

    # Relacionamentos
    versoes: List["VersaoProcesso"] = Relationship(back_populates="processo")
    execucoes: List["Execucao"] = Relationship(back_populates="processo")

class VersaoProcesso(BaseModel, table=True):
    __tablename__ = "versao_processo"
    
    processo_id: UUID = Field(foreign_key="processo.id", index=True)
    version: str = Field(max_length=20) # Ex: 1.0.1
    is_active: bool = Field(default=False)
    package_url: str = Field(max_length=500)
    checksum: Optional[str] = Field(default=None, max_length=64)
    
    processo: Processo = Relationship(back_populates="versoes")

class Execucao(BaseModel, table=True):
    __tablename__ = "execucao"
    
    processo_id: UUID = Field(foreign_key="processo.id", index=True)
    agente_id: Optional[UUID] = Field(default=None, foreign_key="agente.id")
    versao_id: UUID = Field(foreign_key="versao_processo.id")
    
    status: StatusExecucaoEnum = Field(default=StatusExecucaoEnum.QUEUED)
    start_time: Optional[datetime] = Field(default=None)
    end_time: Optional[datetime] = Field(default=None)
    
    # Logs e Relacionamentos
    processo: Processo = Relationship(back_populates="execucoes")
    logs: List["LogExecucao"] = Relationship(back_populates="execucao")

# --- INDEXES DE PERFORMANCE ---
Index("idx_agente_tenant_name", Agente.tenant_id, Agente.name, unique=True)
Index("idx_processo_tenant_name", Processo.tenant_id, Processo.name, unique=True)