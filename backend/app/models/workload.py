# backend/app/models/workload.py
"""
Módulo de workload (filas e exceções).

Define:
- ItemFila: Itens de trabalho em filas de processos
- Excecao: Exceções ocorridas durante execuções
"""

from datetime import datetime
from enum import Enum
from typing import Optional, TYPE_CHECKING
from uuid import UUID

from sqlmodel import Field, Relationship, Column, String, JSON, Index

from .base import BaseModel

if TYPE_CHECKING:
    from .core import Processo, Agente, Execucao


# ==================== ENUMS ====================

class PriorityEnum(str, Enum):
    """Prioridade de item de fila."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class StatusItemFilaEnum(str, Enum):
    """Status de item na fila."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"


class TipoExcecaoEnum(str, Enum):
    """Tipo de exceção."""
    BUSINESS = "business"      # Regra de negócio
    SYSTEM = "system"          # Erro de sistema/infra
    APPLICATION = "application" # Erro de aplicação


class SeverityEnum(str, Enum):
    """Severidade da exceção."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ==================== MODELOS ====================

class ItemFila(BaseModel, table=True):
    """
    Representa um item de trabalho em uma fila de processo.
    
    Gerencia:
    - Prioridade e status do item
    - Retry logic
    - Vinculação com processo e execução
    - Payload de dados (JSON)
    """
    
    __tablename__ = "item_fila"
    
    # Foreign Keys
    processo_id: UUID = Field(
        foreign_key="processo.id",
        nullable=False,
        index=True,
        description="ID do processo ao qual o item pertence"
    )
    
    # Identificação da fila
    queue_name: str = Field(
        max_length=100,
        index=True,
        description="Nome lógico da fila (ex: 'invoices_to_process')"
    )
    
    # Prioridade e status
    priority: PriorityEnum = Field(
        default=PriorityEnum.NORMAL,
        sa_column=Column(String(20), index=True),
        description="Prioridade do item na fila"
    )
    
    status: StatusItemFilaEnum = Field(
        default=StatusItemFilaEnum.PENDING,
        sa_column=Column(String(20), index=True),
        description="Status atual do item"
    )
    
    # Payload do item
    data: dict = Field(
        sa_column=Column(JSON),
        description="Dados do item (payload JSON)"
    )
    
    # Retry logic
    retry_count: int = Field(
        default=0,
        description="Número de tentativas de processamento"
    )
    
    max_retries: int = Field(
        default=3,
        description="Número máximo de tentativas permitidas"
    )
    
    # Processamento
    processed_at: Optional[datetime] = Field(
        default=None,
        description="Data/hora de processamento do item"
    )
    
    processed_by_agente_id: Optional[UUID] = Field(
        default=None,
        foreign_key="agente.id",
        index=True,
        description="ID do agente que processou o item"
    )
    
    execution_id: Optional[UUID] = Field(
        default=None,
        foreign_key="execucao.id",
        index=True,
        description="ID da execução que processou o item"
    )
    
    # Erro
    error_message: Optional[str] = Field(
        default=None,
        description="Mensagem de erro (se falhou)"
    )
    
    # Relacionamentos
    processo: "Processo" = Relationship(
        back_populates="itens_fila",
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    
    agente: Optional["Agente"] = Relationship(
        back_populates="itens_processados",
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    
    execucao: Optional["Execucao"] = Relationship(
        back_populates="itens_fila",
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    
    def __repr__(self) -> str:
        return f"<ItemFila(id={self.id}, queue_name={self.queue_name}, status={self.status})>"


class Excecao(BaseModel, table=True):
    """
    Representa uma exceção ocorrida durante uma execução.
    
    Registra:
    - Tipo e severidade
    - Stack trace
    - Screenshot (caminho)
    - Contexto adicional
    - Status de resolução
    """
    
    __tablename__ = "excecao"
    
    # Foreign Keys
    execucao_id: UUID = Field(
        foreign_key="execucao.id",
        nullable=False,
        index=True,
        description="ID da execução onde ocorreu a exceção"
    )
    
    # Classificação
    tipo: TipoExcecaoEnum = Field(
        sa_column=Column(String(20)),
        description="Tipo de exceção (business/system/application)"
    )
    
    severity: SeverityEnum = Field(
        sa_column=Column(String(20), index=True),
        description="Severidade da exceção"
    )
    
    # Detalhes do erro
    message: str = Field(
        max_length=500,
        description="Mensagem da exceção"
    )
    
    stack_trace: Optional[str] = Field(
        default=None,
        description="Stack trace completo do erro"
    )
    
    screenshot_path: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Caminho para screenshot da tela (se disponível)"
    )
    
    # Contexto adicional
    context: dict = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Dados adicionais sobre o contexto do erro"
    )
    
    # Resolução
    is_resolved: bool = Field(
        default=False,
        index=True,
        description="Exceção foi resolvida/tratada"
    )
    
    resolved_at: Optional[datetime] = Field(
        default=None,
        description="Data/hora de resolução da exceção"
    )
    
    # Relacionamentos
    execucao: "Execucao" = Relationship(
        back_populates="excecoes",
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    
    def __repr__(self) -> str:
        return f"<Excecao(id={self.id}, tipo={self.tipo}, severity={self.severity})>"


# ==================== INDEXES ====================

# ItemFila - otimizado para busca de próximo item da fila
Index('idx_itemfila_tenant_status_priority_created',
      ItemFila.tenant_id,
      ItemFila.status,
      ItemFila.priority.desc(),
      ItemFila.created_at.asc())

Index('idx_itemfila_tenant_queue_status',
      ItemFila.tenant_id,
      ItemFila.queue_name,
      ItemFila.status)

# Excecao
Index('idx_excecao_tenant_execucao',
      Excecao.tenant_id,
      Excecao.execucao_id)

Index('idx_excecao_tenant_severity_resolved',
      Excecao.tenant_id,
      Excecao.severity,
      Excecao.is_resolved)