# backend/app/schemas/workload.py
from datetime import datetime
from typing import Optional, Any, Dict
from uuid import UUID
from pydantic import Field, ConfigDict

from app.models.workload import PriorityEnum, StatusItemFilaEnum, TipoExcecaoEnum, SeverityEnum
from .common import BaseSchema, TimestampMixin, TenantMixin

# ==================== ITEM DE FILA SCHEMAS ====================

class ItemFilaBase(BaseSchema):
    """Campos base para um item de fila."""
    queue_name: str = Field(..., min_length=1, max_length=100, examples=["processamento_faturas"])
    priority: PriorityEnum = Field(default=PriorityEnum.NORMAL)
    payload: Dict[str, Any] = Field(
        ..., 
        description="Dados JSON que o robô usará para o processamento"
    )
    reference: Optional[str] = Field(None, max_length=100, description="ID externo para rastreio")
    deferred_until: Optional[datetime] = None
    max_retries: int = Field(default=3, ge=0)

class ItemFilaCreate(ItemFilaBase):
    """Request para criar novos itens na fila."""
    # Pode ser associado a uma execução específica se iniciado por um processo
    execucao_id: Optional[UUID] = None

class ItemFilaRead(ItemFilaBase, TimestampMixin, TenantMixin):
    """Resposta completa do item da fila."""
    id: UUID
    status: StatusItemFilaEnum
    retry_count: int
    locked_until: Optional[datetime] = None
    locked_by: Optional[UUID] = None
    completed_at: Optional[datetime] = None

# ==================== EXCEÇÃO SCHEMAS ====================

class ExcecaoCreate(BaseSchema):
    """Payload enviado pelo robô quando ocorre um erro."""
    tipo: TipoExcecaoEnum
    severity: SeverityEnum = Field(default=SeverityEnum.MEDIUM)
    message: str = Field(..., min_length=1)
    stack_trace: Optional[str] = None
    screenshot_path: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

class ExcecaoRead(ExcecaoCreate, TimestampMixin, TenantMixin):
    """Leitura de erro para o Dashboard."""
    id: UUID
    item_fila_id: Optional[UUID] = None
    execucao_id: Optional[UUID] = None
    is_resolved: bool
    resolved_at: Optional[datetime] = None

# ==================== CONTROLO DE FLUXO ====================

class WorkloadActionResponse(BaseSchema):
    """Resposta padrão para ações de sucesso/erro do agente."""
    success: bool
    status_final: StatusItemFilaEnum
    message: str