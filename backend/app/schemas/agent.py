# backend/app/schemas/agent.py
"""
Schemas Pydantic para gestão de agentes RPA.

Endpoints suportados:
- GET    /agents          (listagem paginada + filtros)
- GET    /agents/{id}     (detalhe)
- POST   /agents          (criar)
- PUT    /agents/{id}     (atualizar)
- DELETE /agents/{id}     (soft delete)
- POST   /agents/{id}/heartbeat (heartbeat)

[FIX #1]: metadata renomeado para extra_data (padronizado com models)
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import Field, field_validator

from app.models.core import StatusAgenteEnum
from .common import BaseSchema, TenantMixin, TimestampMixin, PaginationParams


# ==================== AGENT BASE SCHEMAS ====================

class AgentBase(BaseSchema):
    """Campos base do agente (compartilhados entre Create/Update)"""
    
    name: str = Field(
        min_length=3,
        max_length=100,
        description="Nome único do agente por tenant",
        examples=["bot-prod-01"]
    )
    
    machine_name: str = Field(
        min_length=2,
        max_length=100,
        description="Hostname da máquina onde o agente roda",
        examples=["worker-prod-01"]
    )
    
    ip_address: Optional[str] = Field(
        default=None,
        max_length=45,
        description="Endereço IP da máquina (IPv4 ou IPv6)",
        examples=["192.168.1.100"]
    )
    
    capabilities: List[str] = Field(
        default_factory=list,
        description="Lista de capabilities do agente",
        examples=[["web", "excel", "pdf"]]
    )
    
    version: str = Field(
        min_length=5,
        max_length=20,
        description="Versão do cliente do agente (semantic versioning)",
        examples=["1.2.0"]
    )
    
    extra_data: dict = Field(
        default_factory=dict,
        description="Dados extras (JSON livre)",
        examples=[{"environment": "production", "region": "us-east-1"}]
    )
    
    @field_validator('capabilities')
    @classmethod
    def validate_capabilities_not_empty(cls, v: List[str]) -> List[str]:
        """Valida que capabilities não está vazio"""
        if not v or len(v) == 0:
            raise ValueError("Agente deve ter pelo menos 1 capability")
        return v
    
    @field_validator('version')
    @classmethod
    def validate_semver(cls, v: str) -> str:
        """Valida semantic versioning básico (X.Y.Z)"""
        import re
        pattern = r'^\d+\.\d+\.\d+$'
        if not re.match(pattern, v):
            raise ValueError(
                "Versão deve seguir semantic versioning (ex: 1.0.0)"
            )
        return v


class AgentCreate(AgentBase):
    """Schema para criar novo agente"""
    
    # Herda todos os campos de AgentBase
    # Status inicial será sempre "offline" (definido no service)
    pass


class AgentUpdate(BaseSchema):
    """Schema para atualizar agente (todos os campos opcionais)"""
    
    name: Optional[str] = Field(
        default=None,
        min_length=3,
        max_length=100
    )
    
    machine_name: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=100
    )
    
    ip_address: Optional[str] = Field(
        default=None,
        max_length=45
    )
    
    status: Optional[StatusAgenteEnum] = Field(
        default=None,
        description="Status manual do agente"
    )
    
    capabilities: Optional[List[str]] = Field(
        default=None
    )
    
    version: Optional[str] = Field(
        default=None,
        min_length=5,
        max_length=20
    )
    
    extra_data: Optional[dict] = Field(
        default=None
    )


class AgentRead(TenantMixin, TimestampMixin):
    """Schema para retornar agente (response)"""
    
    id: UUID = Field(description="ID único do agente")
    
    name: str = Field(description="Nome do agente")
    
    machine_name: str = Field(description="Nome da máquina")
    
    ip_address: str = Field(description="IP do agente")
    
    version: str = Field(description="Versão do agente")
    
    status: StatusAgenteEnum = Field(
        description="Status atual do agente"
    )
    
    last_heartbeat: Optional[datetime] = Field(
        default=None,
        description="Último heartbeat recebido"
    )
    
    capabilities: List[str] = Field(
        default_factory=list,
        description="Capabilities do agente"
    )
    
    extra_data: dict = Field(
        default_factory=dict,
        description="Dados extras"
    )
    
    is_online: bool = Field(
        description="Computed: agente está online? (heartbeat < 5 min)"
    )
    
    @classmethod
    def from_model(cls, agent):
        """
        Factory method que adiciona campo computed 'is_online'.
        
        Considera online se:
        - last_heartbeat existe
        - last_heartbeat < 5 minutos atrás
        - status != maintenance
        """
        from datetime import datetime, timedelta
        
        is_online = False
        if agent.last_heartbeat and agent.status != StatusAgenteEnum.MAINTENANCE:
            time_diff = datetime.utcnow() - agent.last_heartbeat
            is_online = time_diff < timedelta(minutes=5)
        
        # Criar dict do modelo + adicionar is_online
        data = {
            **agent.__dict__,
            "is_online": is_online
        }
        
        return cls(**data)


# ==================== HEARTBEAT SCHEMAS ====================

class HeartbeatRequest(BaseSchema):
    """Schema para enviar heartbeat"""
    
    status: Optional[StatusAgenteEnum] = Field(
        default=StatusAgenteEnum.ONLINE,
        description="Status a ser definido (default: online)"
    )
    
    extra_data: Optional[dict] = Field(
        default=None,
        description="Dados extras a serem merged (não sobrescreve tudo)"
    )


class HeartbeatResponse(BaseSchema):
    """Schema para resposta de heartbeat"""
    
    agent_id: UUID = Field(description="ID do agente")
    last_heartbeat: datetime = Field(description="Último heartbeat")
    status: StatusAgenteEnum = Field(description="Status atual")
    is_online: bool = Field(description="Agente está online?")
    message: str = Field(
        default="Heartbeat registrado com sucesso"
    )


# ==================== FILTER SCHEMAS ====================

class AgentFilterParams(PaginationParams):
    """
    Parâmetros de filtro para listagem de agentes.
    
    Herda de PaginationParams (page, size, skip, limit).
    """
    
    status: Optional[StatusAgenteEnum] = Field(
        default=None,
        description="Filtrar por status específico"
    )
    
    capabilities: Optional[str] = Field(
        default=None,
        description="Filtrar por capabilities (separado por vírgula: 'web,excel')"
    )
    
    machine_name: Optional[str] = Field(
        default=None,
        description="Busca parcial por machine_name (ILIKE)"
    )
    
    is_online: Optional[bool] = Field(
        default=None,
        description="Filtrar apenas agentes online (heartbeat < 5min)"
    )
    
    sort_by: str = Field(
        default="created_at",
        description="Campo para ordenação",
        pattern="^(name|created_at|last_heartbeat|status)$"
    )
    
    sort_order: str = Field(
        default="desc",
        description="Ordem de ordenação",
        pattern="^(asc|desc)$"
    )
    
    @property
    def capabilities_list(self) -> List[str]:
        """Converte string 'web,excel' em lista ['web', 'excel']"""
        if not self.capabilities:
            return []
        return [cap.strip() for cap in self.capabilities.split(",")]