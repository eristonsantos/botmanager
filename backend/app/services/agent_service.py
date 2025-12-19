"""
Serviço de negócio para Agentes RPA.

Encapsula toda a lógica de CRUD, validações e filtros.
Disponível para endpoints e testes.

[FIX #2]: tenant_id agora vem diretamente do JWT (sem query ao BD)
"""

from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.exceptions import NotFoundError, ConflictError
from app.core.logging import get_logger
from app.models import Agente
from app.models.core import StatusAgenteEnum
from app.schemas.agent import (
    AgentCreate,
    AgentFilterParams,
    AgentUpdate,
    HeartbeatRequest,
)


logger = get_logger(__name__)


class AgentService:
    """Service para gerenciar Agentes"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    # ========================================================================
    # LIST / FILTER
    # ========================================================================
    
    async def list_agents(
        self,
        tenant_id: UUID,
        filters: AgentFilterParams
    ) -> Tuple[List[Agente], int]:
        """
        Lista agentes com paginação e filtros.
        
        Args:
            tenant_id: ID do tenant (extraído do JWT)
            filters: Parâmetros de filtro (status, capabilities, machine_name, etc)
        
        Returns:
            Tuple[lista de agentes, total de registros]
        """
        # Build base query
        stmt = select(Agente).where(
            Agente.tenant_id == tenant_id,
            Agente.deleted_at.is_(None)
        )
        
        # Apply filters
        if filters.status:
            stmt = stmt.where(Agente.status == filters.status)
        
        if filters.machine_name:
            stmt = stmt.where(Agente.machine_name.ilike(f"%{filters.machine_name}%"))
        
        # Filter by is_online (heartbeat < 5 minutes)
        if filters.is_online is not None:
            if filters.is_online:
                # Agent is online if last_heartbeat is within 5 minutes
                cutoff = datetime.utcnow() - timedelta(minutes=5)
                stmt = stmt.where(Agente.last_heartbeat > cutoff)
            else:
                # Agent is offline if no heartbeat or heartbeat > 5 minutes ago
                cutoff = datetime.utcnow() - timedelta(minutes=5)
                stmt = stmt.where(
                    (Agente.last_heartbeat.is_(None)) | (Agente.last_heartbeat <= cutoff)
                )
        
        # Filter by capabilities (JSON array contains)
        if filters.capabilities_list:
            for capability in filters.capabilities_list:
                # Busca se a capability está no array JSON
                stmt = stmt.where(
                    Agente.capabilities.astext.contains(capability)
                )
        
        # Count total antes de paginar
        count_stmt = select(func.count()).select_from(Agente).where(
            Agente.tenant_id == tenant_id,
            Agente.deleted_at.is_(None)
        )
        
        # Aplicar mesmos filtros na contagem
        if filters.status:
            count_stmt = count_stmt.where(Agente.status == filters.status)
        if filters.machine_name:
            count_stmt = count_stmt.where(Agente.machine_name.ilike(f"%{filters.machine_name}%"))
        
        # Filter by is_online in count statement
        if filters.is_online is not None:
            if filters.is_online:
                cutoff = datetime.utcnow() - timedelta(minutes=5)
                count_stmt = count_stmt.where(Agente.last_heartbeat > cutoff)
            else:
                cutoff = datetime.utcnow() - timedelta(minutes=5)
                count_stmt = count_stmt.where(
                    (Agente.last_heartbeat.is_(None)) | (Agente.last_heartbeat <= cutoff)
                )
        
        total = await self.session.scalar(count_stmt)
        
        # Ordenar
        if filters.sort_by == "name":
            order_col = Agente.name
        elif filters.sort_by == "last_heartbeat":
            order_col = Agente.last_heartbeat
        elif filters.sort_by == "status":
            order_col = Agente.status
        else:  # created_at (padrão)
            order_col = Agente.created_at
        
        if filters.sort_order == "asc":
            stmt = stmt.order_by(order_col.asc())
        else:
            stmt = stmt.order_by(order_col.desc())
        
        # Paginar
        stmt = stmt.offset(filters.skip).limit(filters.limit)
        
        result = await self.session.execute(stmt)
        agents = result.scalars().all()
        
        logger.info(f"Listed {len(agents)} agents for tenant {tenant_id} (total: {total})")
        
        return agents, total or 0
    
    # ========================================================================
    # CREATE
    # ========================================================================
    
    async def create_agent(
        self,
        tenant_id: UUID,
        data: AgentCreate
    ) -> Agente:
        """
        Cria novo agente.
        
        Validações:
        - Nome único por tenant
        
        Args:
            tenant_id: ID do tenant (extraído do JWT)
            data: Dados do agente a criar
        
        Returns:
            Agente criado
        
        Raises:
            ConflictError: Se nome já existe no tenant
        """
        # Verificar nome único por tenant
        existing = await self._get_by_name(tenant_id, data.name)
        if existing:
            raise ConflictError(
                message=f"Nome '{data.name}' já existe neste tenant",
                details={"field": "name", "value": data.name}
            )
        
        # Criar agente
        agent = Agente(
            tenant_id=tenant_id,
            name=data.name,
            machine_name=data.machine_name,
            ip_address=data.ip_address,
            version=data.version,
            capabilities=data.capabilities or {},
            status=StatusAgenteEnum.OFFLINE,  # Padrão offline
            is_active=True,
            last_heartbeat=None,
            extra_data=data.extra_data or {}
        )
        
        self.session.add(agent)
        await self.session.commit()
        await self.session.refresh(agent)
        
        logger.info(f"Agent created: {agent.id} ({agent.name}) for tenant {tenant_id}")
        
        return agent
    
    # ========================================================================
    # GET / DETAIL
    # ========================================================================
    
    async def get_agent(
        self,
        tenant_id: UUID,
        agent_id: UUID
    ) -> Agente:
        """
        Obtém agente por ID.
        
        Args:
            tenant_id: ID do tenant (extraído do JWT)
            agent_id: ID do agente
        
        Returns:
            Agente encontrado
        
        Raises:
            NotFoundError: Se agente não existe
        """
        stmt = select(Agente).where(
            Agente.id == agent_id,
            Agente.tenant_id == tenant_id,
            Agente.deleted_at.is_(None)
        )
        
        result = await self.session.execute(stmt)
        agent = result.scalar_one_or_none()
        
        if not agent:
            raise NotFoundError(
                resource="Agent",
                identifier=str(agent_id),
                details={"tenant_id": str(tenant_id)}
            )
        
        return agent
    
    async def _get_by_name(
        self,
        tenant_id: UUID,
        name: str
    ) -> Optional[Agente]:
        """Helper: Busca agente por nome no tenant"""
        stmt = select(Agente).where(
            Agente.tenant_id == tenant_id,
            Agente.name == name,
            Agente.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    # ========================================================================
    # UPDATE
    # ========================================================================
    
    async def update_agent(
        self,
        tenant_id: UUID,
        agent_id: UUID,
        data: AgentUpdate
    ) -> Agente:
        """
        Atualiza agente.
        
        Validações:
        - Novo nome deve ser único por tenant (se fornecido)
        
        Args:
            tenant_id: ID do tenant (extraído do JWT)
            agent_id: ID do agente
            data: Dados a atualizar
        
        Returns:
            Agente atualizado
        
        Raises:
            NotFoundError: Se agente não existe
            ConflictError: Se novo nome já existe
        """
        # Buscar agente
        agent = await self.get_agent(tenant_id, agent_id)

        # Obter apenas os campos definidos no update usando Pydantic 2
        update_data = data.model_dump(exclude_unset=True)

        # Validar nome único (se fornecido e diferente)
        if "name" in update_data and update_data["name"] != agent.name:
            existing = await self._get_by_name(tenant_id, update_data["name"])
            if existing:
                raise ConflictError(
                    message=f"Nome '{update_data['name']}' já existe neste tenant",
                    details={"field": "name", "value": update_data["name"]}
                )

        # Atualizar campos fornecidos
        for field, value in update_data.items():
            if hasattr(agent, field):
                setattr(agent, field, value)

        await self.session.commit()
        await self.session.refresh(agent)
        
        logger.info(f"Agent updated: {agent.id} ({agent.name})")
        
        return agent
    
    # ========================================================================
    # DELETE (soft delete)
    # ========================================================================
    
    async def delete_agent(
        self,
        tenant_id: UUID,
        agent_id: UUID
    ) -> None:
        """
        Soft delete de agente.
        
        Args:
            tenant_id: ID do tenant (extraído do JWT)
            agent_id: ID do agente
        
        Raises:
            NotFoundError: Se agente não existe
        """
        agent = await self.get_agent(tenant_id, agent_id)
        
        agent.deleted_at = datetime.utcnow()
        await self.session.commit()
        
        logger.info(f"Agent deleted (soft): {agent.id} ({agent.name})")
    
    # ========================================================================
    # HEARTBEAT
    # ========================================================================
    
    async def record_heartbeat(
        self,
        tenant_id: UUID,
        agent_id: UUID,
        data: HeartbeatRequest
    ) -> Agente:
        """
        Registra heartbeat do agente.

        Atualiza:
        - Status
        - last_heartbeat
        - extra_data (se fornecido)

        Args:
            tenant_id: ID do tenant (extraído do JWT)
            agent_id: ID do agente
            data: Dados do heartbeat (status e extra_data opcional)

        Returns:
            Agente atualizado

        Raises:
            NotFoundError: Se agente não existe
        """
        agent = await self.get_agent(tenant_id, agent_id)

        agent.status = data.status
        agent.last_heartbeat = datetime.utcnow()

        if data.extra_data:
            # Merge extra_data instead of replacing
            if agent.extra_data is None:
                agent.extra_data = {}
            agent.extra_data.update(data.extra_data)

        await self.session.commit()
        await self.session.refresh(agent)
        
        logger.info(
            f"Heartbeat recorded: agent {agent.id} - status: {agent.status} - "
            f"last_heartbeat: {agent.last_heartbeat}"
        )
        
        return agent