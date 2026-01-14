# backend/app/schemas/workload.py
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

# IMPORTANTE: Importamos os Enums do modelo para garantir consistência
from app.models.workload import PriorityEnum, StatusItemFilaEnum, TipoExcecaoEnum, SeverityEnum

# --- ITEM FILA ---

class ItemFilaCreate(BaseModel):
    queue_name: str
    reference: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    
    # Valida string "normal" e converte para Enum automaticamente
    priority: PriorityEnum = PriorityEnum.NORMAL 
    
    max_retries: int = 3
    processo_id: Optional[UUID] = None

class ItemFilaUpdate(BaseModel):
    status: Optional[StatusItemFilaEnum] = None
    payload: Optional[Dict[str, Any]] = None
    retry_count: Optional[int] = None
    locked_by: Optional[UUID] = None

class ItemFilaRead(BaseModel):
    id: UUID
    tenant_id: UUID
    queue_name: str
    status: StatusItemFilaEnum
    priority: PriorityEnum
    payload: Dict[str, Any]
    reference: Optional[str] = None
    retry_count: int
    max_retries: int
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None # Campo calculado ou real se tiver
    locked_by: Optional[UUID] = None
    
    model_config = ConfigDict(from_attributes=True)

class WorkloadActionResponse(BaseModel):
    success: bool
    message: str
    item_id: Optional[UUID] = None

# --- EXCEÇÃO ---

class ExcecaoCreate(BaseModel):
    tipo: TipoExcecaoEnum = TipoExcecaoEnum.SYSTEM
    severity: SeverityEnum = SeverityEnum.MEDIUM
    message: str
    stack_trace: Optional[str] = None
    execucao_id: Optional[UUID] = None
    item_fila_id: Optional[UUID] = None

class ExcecaoRead(BaseModel):
    id: UUID
    tipo: TipoExcecaoEnum
    severity: SeverityEnum
    message: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)