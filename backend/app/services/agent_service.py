# backend/app/services/agent_service.py
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.exceptions import NotFoundError, ConflictError
from app.core.logging import get_logger
from app.models.core import Agente, StatusAgenteEnum
from app.schemas.agent import AgentCreate, AgentUpdate, AgentFilterParams, HeartbeatRequest

logger = get_logger(__name__)

class AgentService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_agent(self, tenant_id: UUID, data: AgentCreate) -> Agente:
        # Validação de nome único por tenant
        stmt = select(Agente).where(
            Agente.tenant_id == tenant_id, 
            Agente.name == data.name,
            Agente.deleted_at == None
        )
        existing = await self.session.execute(stmt)
        if existing.scalar_one_or_none():
            raise ConflictError(f"Agente com nome '{data.name}' já existe neste tenant.")

        # Inserção automática de tenant_id via BaseModel
        agente = Agente(**data.model_dump(), tenant_id=tenant_id)
        self.session.add(agente)
        await self.session.commit()
        await self.session.refresh(agente)
        return agente

    async def record_heartbeat(self, tenant_id: UUID, agent_id: UUID, data: HeartbeatRequest) -> Agente:
        """Atualiza o estado do robô em tempo real."""
        stmt = select(Agente).where(Agente.id == agent_id, Agente.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        agente = result.scalar_one_or_none()

        if not agente:
            raise NotFoundError(resource="Agente", identifier=agent_id)

        agente.status = data.status
        agente.last_heartbeat = datetime.now(timezone.utc)
        
        # Merge de dados extras (metadados da máquina, versão do SO, etc)
        if data.extra_data:
            agente.extra_data = {**(agente.extra_data or {}), **data.extra_data}

        await self.session.commit()
        await self.session.refresh(agente)
        return agente

    async def get_online_agents_count(self, tenant_id: UUID) -> int:
        """Helper para dashboards: agentes que enviaram sinal nos últimos 5 min."""
        threshold = datetime.now(timezone.utc) - timedelta(minutes=5)
        stmt = select(func.count(Agente.id)).where(
            Agente.tenant_id == tenant_id,
            Agente.last_heartbeat >= threshold,
            Agente.status != StatusAgenteEnum.OFFLINE
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0