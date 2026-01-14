from datetime import datetime
from typing import Tuple, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func, col, or_

# CORREÇÃO CRÍTICA: Importamos 'Agente' e apelidamos de 'Agent'
from app.models import Agente as Agent 
from app.schemas.agent import (
    AgentCreate, 
    AgentUpdate, 
    AgentFilterParams,
    HeartbeatRequest
)
from app.core.exceptions import NotFoundError, ConflictError
from app.models.core import StatusAgenteEnum

class AgentService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_agent(self, tenant_id: UUID, data: AgentCreate) -> Agent:
        """Cria novo agente validando duplicidade de nome no tenant"""
        stmt = select(Agent).where(
            Agent.tenant_id == tenant_id,
            Agent.name == data.name,
            Agent.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)
        if result.scalar_one_or_none():
            raise ConflictError(
                message=f"Agente com nome '{data.name}' já existe neste tenant.",
                details={"field": "name"}
            )
        
        # Converte o schema (AgentCreate) para o model (Agente)
        # O model_dump gera um dict. O Agente aceita kwargs.
        agent = Agent(
            tenant_id=tenant_id,
            **data.model_dump()
        )
        
        self.session.add(agent)
        await self.session.commit()
        await self.session.refresh(agent)
        return agent

    async def list(
        self, 
        tenant_id: UUID, 
        filters: AgentFilterParams
    ) -> Tuple[List[Agent], int]:
        
        query = select(Agent).where(
            Agent.tenant_id == tenant_id,
            Agent.deleted_at.is_(None)
        )
        
        if filters.status:
            status_list = filters.status.split(",")
            query = query.where(col(Agent.status).in_(status_list))
            
        if filters.machine_name:
            query = query.where(col(Agent.machine_name).ilike(f"%{filters.machine_name}%"))

        # Contagem
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar_one()
        
        # Ordenação
        if hasattr(Agent, filters.sort_by):
            column = getattr(Agent, filters.sort_by)
            if filters.sort_order == "desc":
                query = query.order_by(column.desc())
            else:
                query = query.order_by(column.asc())
        
        # Paginação
        query = query.offset((filters.page - 1) * filters.size).limit(filters.size)
        
        result = await self.session.execute(query)
        return result.scalars().all(), total

    async def get_agent(self, tenant_id: UUID, agent_id: UUID) -> Agent:
        stmt = select(Agent).where(
            Agent.id == agent_id,
            Agent.tenant_id == tenant_id,
            Agent.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)
        agent = result.scalar_one_or_none()
        
        if not agent:
            raise NotFoundError(resource="Agente", identifier=str(agent_id))
            
        return agent

    async def update_agent(
        self, 
        tenant_id: UUID, 
        agent_id: UUID, 
        data: AgentUpdate
    ) -> Agent:
        agent = await self.get_agent(tenant_id, agent_id)
        
        update_data = data.model_dump(exclude_unset=True)
        
        if "name" in update_data and update_data["name"] != agent.name:
            stmt = select(Agent).where(
                Agent.tenant_id == tenant_id,
                Agent.name == update_data["name"],
                Agent.id != agent_id,
                Agent.deleted_at.is_(None)
            )
            result = await self.session.execute(stmt)
            if result.scalar_one_or_none():
                raise ConflictError(message=f"Nome '{update_data['name']}' já em uso.")
        
        for key, value in update_data.items():
            setattr(agent, key, value)
            
        self.session.add(agent)
        await self.session.commit()
        await self.session.refresh(agent)
        return agent

    async def delete_agent(self, tenant_id: UUID, agent_id: UUID):
        agent = await self.get_agent(tenant_id, agent_id)
        agent.deleted_at = datetime.utcnow()
        agent.status = "offline" # Ou StatusAgenteEnum.OFFLINE
        
        self.session.add(agent)
        await self.session.commit()

    async def record_heartbeat(
        self, 
        tenant_id: UUID, 
        agent_id: UUID, 
        data: HeartbeatRequest
    ) -> Agent:
        stmt = select(Agent).where(
            Agent.id == agent_id,
            Agent.tenant_id == tenant_id
        )
        result = await self.session.execute(stmt)
        agent = result.scalar_one_or_none()
        
        if not agent:
            raise NotFoundError(resource="Agente", identifier=str(agent_id))
            
        agent.last_heartbeat = datetime.utcnow()
        
        if data.status:
            agent.status = data.status
            
        if data.extra_data:
            if not agent.extra_data:
                agent.extra_data = {}
            agent.extra_data.update(data.extra_data)
            
        self.session.add(agent)
        await self.session.commit()
        await self.session.refresh(agent)
        return agent