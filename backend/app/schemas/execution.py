# backend/app/schemas/execution.py
"""
Schemas Pydantic para gestão de Execuções RPA.

Endpoints suportados (Fase 5B):
- POST /executions/trigger    (criar/disparar)
- GET  /executions            (listar com filtros)
- GET  /executions/{id}       (detalhe)
- POST /executions/{id}/stop  (parar)
- GET  /executions/stats/summary (dashboard)
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.models.core import StatusExecucaoEnum, TriggerTypeEnum
from .common import BaseSchema, TenantMixin, TimestampMixin, PaginationParams


# ==================== BASE SCHEMAS ====================

class ExecutionBase(BaseSchema):
    """Campos base compartilhados"""
    status: StatusExecucaoEnum = Field(
        default=StatusExecucaoEnum.QUEUED,
        description="Estado atual da execução"
    )


# ==================== CREATE / TRIGGER ====================

class ExecutionCreate(BaseSchema):
    """
    Schema para disparar uma nova execução (Trigger).
    """
    processo_id: UUID = Field(
        ...,
        description="ID do processo a ser executado"
    )
    
    agente_id: Optional[UUID] = Field(
        default=None,
        description="Opcional: Forçar execução em um robô específico"
    )
    
    trigger_type: TriggerTypeEnum = Field(
        default=TriggerTypeEnum.MANUAL,
        description="Origem do disparo (manual, cron, api)"
    )
    
    input_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Argumentos de entrada para o robô (JSON)"
    )


class ExecutionUpdate(BaseSchema):
    """
    Schema para atualização de status (usado pelo Robô/Service).
    """
    status: StatusExecucaoEnum
    
    error_details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Detalhes do erro caso falhe"
    )
    
    # Campos internos de controle
    end_time: Optional[datetime] = None


# ==================== READ ====================

class ExecutionRead(ExecutionBase, TenantMixin, TimestampMixin):
    """
    Schema de resposta completo da execução.
    """
    id: UUID
    processo_id: UUID
    versao_id: UUID
    agente_id: Optional[UUID] = None
    
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    # Campos computados/extras
    duration_seconds: Optional[float] = Field(
        default=None,
        description="Duração da execução em segundos"
    )
    
    processo_name: Optional[str] = Field(
        default=None, 
        description="Nome do processo (se join realizado)"
    )
    
    agente_name: Optional[str] = Field(
        default=None,
        description="Nome do robô (se join realizado)"
    )

    @model_validator(mode='after')
    def compute_duration(self):
        """Calcula duração se start_time e end_time existirem"""
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            self.duration_seconds = round(delta.total_seconds(), 2)
        elif self.start_time and self.status == StatusExecucaoEnum.RUNNING:
            # Duração "até agora" se estiver rodando
            delta = datetime.utcnow() - self.start_time
            self.duration_seconds = round(delta.total_seconds(), 2)
        return self


# ==================== FILTERS ====================

class ExecutionFilterParams(PaginationParams):
    """
    Filtros para listagem de histórico.
    """
    processo_id: Optional[UUID] = None
    agente_id: Optional[UUID] = None
    
    status: Optional[StatusExecucaoEnum] = None
    trigger_type: Optional[TriggerTypeEnum] = None
    
    start_date: Optional[datetime] = Field(
        default=None,
        description="Filtrar execuções a partir desta data"
    )
    
    end_date: Optional[datetime] = Field(
        default=None,
        description="Filtrar execuções até esta data"
    )
    
    sort_by: str = Field(default="created_at")
    sort_order: str = Field(default="desc")


# ==================== DASHBOARD / SUMMARY ====================

class ExecutionSummary(BaseSchema):
    """
    Dados agregados para dashboards.
    """
    total_24h: int = 0
    success_rate: float = 0.0  # Porcentagem 0-100
    avg_duration_seconds: float = 0.0
    
    by_status: Dict[str, int] = Field(
        default_factory=dict,
        description="Contagem por status (queued, running, etc)"
    )
    
    last_executions: List[ExecutionRead] = Field(
        default_factory=list,
        description="Top 5 últimas execuções"
    )


# ==================== ACTIONS ====================

class ExecutionActionResponse(BaseSchema):
    """Resposta para ações de controle (stop, retry)"""
    success: bool
    message: str
    execution_id: Optional[UUID] = None
    new_status: Optional[StatusExecucaoEnum] = None