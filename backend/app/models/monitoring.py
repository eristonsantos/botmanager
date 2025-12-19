# backend/app/models/monitoring.py
"""
Módulo de monitoramento e observabilidade.

Define:
- AuditoriaEvento: Auditoria de ações de usuários
- LogExecucao: Logs de execuções de processos
- LogMetadata: Metadados estruturados de logs
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, TYPE_CHECKING
from uuid import UUID

from sqlmodel import Field, Relationship, Column, String, JSON, Index, Text

from .base import BaseModel

if TYPE_CHECKING:
    from .tenant import User
    from .core import Execucao


# ==================== ENUMS ====================

class ActionEnum(str, Enum):
    """Ações auditáveis no sistema."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    CANCEL = "cancel"
    LOGIN = "login"
    LOGOUT = "logout"


class LogLevelEnum(str, Enum):
    """Níveis de log."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class TipoMetadataEnum(str, Enum):
    """Tipo de dado em metadados."""
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    JSON = "json"


# ==================== MODELOS ====================

class AuditoriaEvento(BaseModel, table=True):
    """
    Representa um evento de auditoria no sistema.
    
    Registra:
    - Quem fez a ação (user_id)
    - O que foi feito (action)
    - Em qual entidade (entity_type, entity_id)
    - Valores antes/depois (old_values, new_values)
    - Contexto técnico (IP, User-Agent)
    """
    
    __tablename__ = "auditoria_evento"
    
    # Foreign Keys
    user_id: Optional[UUID] = Field(
        default=None,
        foreign_key="user.id",
        index=True,
        description="ID do usuário que executou a ação (None para ações de sistema)"
    )
    
    # Identificação da entidade
    entity_type: str = Field(
        max_length=50,
        index=True,
        description="Tipo de entidade (ex: 'Processo', 'Agente', 'Execucao')"
    )
    
    entity_id: UUID = Field(
        index=True,
        description="ID da entidade afetada"
    )
    
    # Ação
    action: ActionEnum = Field(
        sa_column=Column(String(20), index=True),
        description="Ação executada"
    )
    
    # Valores
    old_values: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Valores anteriores (para UPDATE/DELETE)"
    )
    
    new_values: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Valores novos (para CREATE/UPDATE)"
    )
    
    # Contexto técnico
    ip_address: Optional[str] = Field(
        default=None,
        max_length=45,  # IPv6
        description="Endereço IP de origem"
    )
    
    user_agent: Optional[str] = Field(
        default=None,
        max_length=500,
        description="User-Agent do cliente"
    )
    
    # Relacionamentos
    user: Optional["User"] = Relationship(
        back_populates="auditorias",
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    
    def __repr__(self) -> str:
        return f"<AuditoriaEvento(id={self.id}, action={self.action}, entity_type={self.entity_type})>"


class LogExecucao(BaseModel, table=True):
    """
    Representa um log de execução de processo.
    
    Estrutura de logging estruturado:
    - Níveis de log (debug, info, warning, error, critical)
    - Correlation ID para rastreamento distribuído
    - Source para identificar origem do log
    - Metadados extensíveis via relacionamento
    """
    
    __tablename__ = "log_execucao"
    
    # Foreign Keys
    execucao_id: UUID = Field(
        foreign_key="execucao.id",
        nullable=False,
        index=True,
        description="ID da execução associada"
    )
    
    # Classificação
    level: LogLevelEnum = Field(
        default=LogLevelEnum.INFO,
        sa_column=Column(String(20), index=True),
        description="Nível do log"
    )
    
    # Mensagem
    message: str = Field(
        sa_column=Column(Text),
        description="Mensagem do log"
    )
    
    # Rastreamento
    correlation_id: str = Field(
        max_length=36,
        index=True,
        description="Correlation ID (mesmo da execução)"
    )
    
    source: str = Field(
        max_length=100,
        description="Origem do log (módulo/função)"
    )
    
    # Dados adicionais inline
    extra: dict = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Campos extras não estruturados"
    )
    
    # Relacionamentos
    execucao: "Execucao" = Relationship(
        back_populates="logs",
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    
    metadados: List["LogMetadata"] = Relationship(
        back_populates="log",
        sa_relationship_kwargs={"lazy": "selectin", "cascade": "all, delete-orphan"}
    )
    
    def __repr__(self) -> str:
        return f"<LogExecucao(id={self.id}, level={self.level}, execucao_id={self.execucao_id})>"


class LogMetadata(BaseModel, table=True):
    """
    Representa metadados estruturados de um log.
    
    Permite armazenar campos adicionais de forma queryável:
    - Key-value pairs
    - Tipagem de valores
    - Facilita busca e agregação
    
    Exemplo:
    - key="duration_ms", value="1250", tipo="number"
    - key="user_action", value="click_button", tipo="string"
    """
    
    __tablename__ = "log_metadata"
    
    # Foreign Keys
    log_execucao_id: UUID = Field(
        foreign_key="log_execucao.id",
        nullable=False,
        index=True,
        description="ID do log associado"
    )
    
    # Dados
    key: str = Field(
        max_length=50,
        index=True,
        description="Chave do metadado"
    )
    
    value: str = Field(
        description="Valor do metadado (armazenado como string)"
    )
    
    tipo: TipoMetadataEnum = Field(
        sa_column=Column(String(20)),
        description="Tipo do valor (para desserialização)"
    )
    
    # Relacionamentos
    log: LogExecucao = Relationship(
        back_populates="metadados",
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    
    def __repr__(self) -> str:
        return f"<LogMetadata(id={self.id}, key={self.key}, value={self.value[:20]})>"


# ==================== INDEXES ====================

# AuditoriaEvento
Index('idx_auditoria_tenant_entity',
      AuditoriaEvento.tenant_id,
      AuditoriaEvento.entity_type,
      AuditoriaEvento.entity_id)

Index('idx_auditoria_tenant_action_created',
      AuditoriaEvento.tenant_id,
      AuditoriaEvento.action,
      AuditoriaEvento.created_at.desc())

Index('idx_auditoria_user', AuditoriaEvento.user_id)

# LogExecucao
Index('idx_log_tenant_execucao_created',
      LogExecucao.tenant_id,
      LogExecucao.execucao_id,
      LogExecucao.created_at.asc())

Index('idx_log_correlation', LogExecucao.correlation_id)
Index('idx_log_level', LogExecucao.level)

# LogMetadata
Index('idx_logmetadata_log_key',
      LogMetadata.log_execucao_id,
      LogMetadata.key)