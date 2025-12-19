# backend/app/models/core.py
"""
Módulo core com modelos principais do orquestrador RPA.

Define:
- Agente: Robôs/Workers que executam automações
- Processo: Definição de automações
- VersaoProcesso: Versionamento de processos
- Execucao: Registro de execuções de processos
"""

from datetime import datetime
from enum import Enum
from typing import Optional, TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship, Column, String, JSON, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Column


from .base import BaseModel

if TYPE_CHECKING:
    from .workload import ItemFila, Excecao
    from .governance import Asset, Agendamento
    from .monitoring import LogExecucao


# ==================== ENUMS ====================

class StatusAgenteEnum(str, Enum):
    """Status do agente RPA."""
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    MAINTENANCE = "maintenance"


class TipoProcessoEnum(str, Enum):
    """Tipo de processo RPA."""
    ATTENDED = "attended"        # Requer interação humana
    UNATTENDED = "unattended"    # Totalmente automatizado
    HYBRID = "hybrid"            # Misto


class StatusExecucaoEnum(str, Enum):
    """Status de execução de processo."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class TriggerTypeEnum(str, Enum):
    """Tipo de gatilho que iniciou a execução."""
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    QUEUE = "queue"
    API = "api"


# ==================== MODELOS ====================

class Agente(BaseModel, table=True):
    __tablename__ = "agente"

    # Identificação
    name: str = Field(
        max_length=100,
        index=True,
        description="Nome único do agente por tenant",
    )

    machine_name: str = Field(
        max_length=100,
        description="Hostname da máquina onde o agente roda",
    )

    ip_address: Optional[str] = Field(
        default=None,
        max_length=45,  # IPv6
        description="Endereço IP da máquina",
    )

    # Status e heartbeat
    status: StatusAgenteEnum = Field(
        default=StatusAgenteEnum.OFFLINE,
        sa_column=Column(String(20), index=True),
        description="Status atual do agente",
    )

    last_heartbeat: Optional[datetime] = Field(
        default=None,
        index=True,
        description="Último heartbeat recebido do agente",
    )

    # Capabilities e versão
    capabilities: dict = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Capabilities do agente (ex: ['web', 'excel', 'sap'])",
    )

    version: str = Field(
        max_length=20,
        description="Versão do cliente do agente (ex: '1.0.0')",
    )

    # Metadados adicionais
    extra_data: dict = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Informações adicionais sobre o agente",
    )

    # Relacionamentos (SQLAlchemy 2.0 typed + SQLModel Relationship)
    execucoes: Mapped[list["Execucao"]] = Relationship(
        back_populates="agente",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    itens_processados: Mapped[list["ItemFila"]] = Relationship(
        back_populates="agente",
        sa_relationship_kwargs={"lazy": "selectin"},
    )


class Processo(BaseModel, table=True):
    __tablename__ = "processo"

    name: str = Field(
        max_length=100,
        index=True,
        description="Nome único do processo por tenant",
    )

    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Descrição do processo",
    )

    tipo: TipoProcessoEnum = Field(
        sa_column=Column(String(20)),
        description="Tipo de processo (attended/unattended/hybrid)",
    )

    is_active: bool = Field(
        default=True,
        index=True,
        description="Processo ativo no sistema",
    )

    tags: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False),
        description="Tags para categorização (ex: ['financeiro', 'urgente'])",
    )

    extra_data: dict = Field(
        default_factory=dict,
        sa_column=Column(JSONB),
        description="Metadados adicionais do processo",
    )

    versoes: Mapped[list["VersaoProcesso"]] = Relationship(
        back_populates="processo",
        sa_relationship_kwargs={"lazy": "selectin", "cascade": "all, delete-orphan"},
    )

    execucoes: Mapped[list["Execucao"]] = Relationship(
        back_populates="processo",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    itens_fila: Mapped[list["ItemFila"]] = Relationship(
        back_populates="processo",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    assets: Mapped[list["Asset"]] = Relationship(
        back_populates="processo",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    agendamentos: Mapped[list["Agendamento"]] = Relationship(
        back_populates="processo",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    def __repr__(self) -> str:
        return f"<Processo(id={self.id}, name={self.name}, tipo={self.tipo})>"


class VersaoProcesso(BaseModel, table=True):
    __tablename__ = "versao_processo"

    processo_id: UUID = Field(
        foreign_key="processo.id",
        nullable=False,
        index=True,
        description="ID do processo pai",
    )

    version: str = Field(
        max_length=20,
        description="Versão semântica (ex: '1.0.0', '2.1.3')",
    )

    package_path: str = Field(
        max_length=500,
        description="Caminho do pacote/código da versão",
    )

    is_active: bool = Field(
        default=False,
        index=True,
        description="Versão ativa para novas execuções",
    )

    release_notes: Optional[str] = Field(
        default=None,
        description="Notas de release desta versão",
    )

    config: dict = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Configurações específicas desta versão",
    )

    processo: Mapped["Processo"] = Relationship(
        back_populates="versoes",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    execucoes: Mapped[list["Execucao"]] = Relationship(
        back_populates="versao_processo",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    def __repr__(self) -> str:
        return f"<VersaoProcesso(id={self.id}, processo_id={self.processo_id}, version={self.version})>"


class Execucao(BaseModel, table=True):
    __tablename__ = "execucao"

    processo_id: UUID = Field(foreign_key="processo.id", nullable=False, index=True)
    versao_processo_id: UUID = Field(foreign_key="versao_processo.id", nullable=False, index=True)
    agente_id: UUID = Field(foreign_key="agente.id", nullable=False, index=True)

    status: StatusExecucaoEnum = Field(
        default=StatusExecucaoEnum.QUEUED,
        sa_column=Column(String(20), index=True),
        description="Status atual da execução",
    )

    started_at: Optional[datetime] = Field(default=None, description="Data/hora de início da execução")
    finished_at: Optional[datetime] = Field(default=None, description="Data/hora de término da execução")
    duration_seconds: Optional[int] = Field(default=None, description="Duração total da execução em segundos")

    trigger_type: TriggerTypeEnum = Field(
        sa_column=Column(String(20)),
        description="Tipo de gatilho que iniciou a execução",
    )

    correlation_id: str = Field(
        default_factory=lambda: str(uuid4()),
        max_length=36,
        index=True,
        description="UUID para rastreamento distribuído",
    )

    input_data: dict = Field(default_factory=dict, sa_column=Column(JSON), description="Parâmetros de entrada")
    output_data: dict = Field(default_factory=dict, sa_column=Column(JSON), description="Resultado da execução")

    error_message: Optional[str] = Field(default=None, description="Mensagem de erro (se houver)")
    retry_count: int = Field(default=0, description="Número de tentativas de re-execução")

    processo: Mapped["Processo"] = Relationship(
        back_populates="execucoes",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    versao_processo: Mapped["VersaoProcesso"] = Relationship(
        back_populates="execucoes",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    agente: Mapped["Agente"] = Relationship(
        back_populates="execucoes",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    logs: Mapped[list["LogExecucao"]] = Relationship(
        back_populates="execucao",
        sa_relationship_kwargs={"lazy": "selectin", "cascade": "all, delete-orphan"},
    )

    excecoes: Mapped[list["Excecao"]] = Relationship(
        back_populates="execucao",
        sa_relationship_kwargs={"lazy": "selectin", "cascade": "all, delete-orphan"},
    )

    itens_fila: Mapped[list["ItemFila"]] = Relationship(
        back_populates="execucao",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    def __repr__(self) -> str:
        return f"<Execucao(id={self.id}, processo_id={self.processo_id}, status={self.status})>"


# ==================== INDEXES ====================

# Agente
Index("idx_agente_tenant_name", Agente.tenant_id, Agente.name, unique=True)
Index("idx_agente_tenant_status", Agente.tenant_id, Agente.status)
Index("idx_agente_tenant_heartbeat", Agente.tenant_id, Agente.last_heartbeat)

# Processo
Index("idx_processo_tenant_name", Processo.tenant_id, Processo.name, unique=True)
Index("idx_processo_tenant_active", Processo.tenant_id, Processo.is_active)

# VersaoProcesso
Index(
    "idx_versao_tenant_processo_version",
    VersaoProcesso.tenant_id,
    VersaoProcesso.processo_id,
    VersaoProcesso.version,
    unique=True,
)
Index("idx_versao_processo_active", VersaoProcesso.processo_id, VersaoProcesso.is_active)

# Execucao
Index(
    "idx_execucao_tenant_status_created",
    Execucao.tenant_id,
    Execucao.status,
    Execucao.created_at.desc(),
)
Index(
    "idx_execucao_tenant_processo_created",
    Execucao.tenant_id,
    Execucao.processo_id,
    Execucao.created_at.desc(),
)
Index("idx_execucao_correlation", Execucao.correlation_id)
