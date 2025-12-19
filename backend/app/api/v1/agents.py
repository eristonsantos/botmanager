"""
Endpoints REST para gestão de agentes RPA.

Rotas:
- GET    /agents              → Listar (paginado + filtros)
- GET    /agents/{id}         → Detalhe
- POST   /agents              → Criar
- PUT    /agents/{id}         → Atualizar
- DELETE /agents/{id}         → Soft delete
- POST   /agents/{id}/heartbeat → Registrar heartbeat
"""

from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import get_current_user_id
from app.core.logging import get_logger
from app.core.exceptions import NotFoundError
from app.models import User
from app.models.core import StatusAgenteEnum
from app.services.agent_service import AgentService
from app.schemas.agent import (
    AgentCreate,
    AgentRead,
    AgentUpdate,
    AgentFilterParams,
    HeartbeatRequest,
    HeartbeatResponse,
)
from app.schemas.common import PaginatedResponse, MessageResponse
from sqlmodel import select


logger = get_logger(__name__)

router = APIRouter(prefix="/agents", tags=["Agents"])

# ============================================================================
# HELPERS
# ============================================================================

async def get_current_tenant_id(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session)
) -> UUID:
    """Extrai tenant_id do usuário autenticado"""
    # Converter string para UUID se necessário
    if isinstance(user_id, str):
        try:
            user_id_uuid = UUID(user_id)
        except ValueError:
            raise NotFoundError(resource="User", identifier=user_id)
    else:
        user_id_uuid = user_id
    
    stmt = select(User).where(User.id == user_id_uuid)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise NotFoundError(resource="User", identifier=str(user_id))
    
    return user.tenant_id


def _agent_to_read(agent) -> AgentRead:
    """Converte model Agente para schema AgentRead com is_online computado"""
    from datetime import datetime, timedelta
    
    is_online = False
    if agent.last_heartbeat:
        time_diff = datetime.utcnow() - agent.last_heartbeat.replace(tzinfo=None)
        is_online = (
            time_diff < timedelta(minutes=5) and 
            agent.status != StatusAgenteEnum.MAINTENANCE
        )
    
    # Converter capabilities (dict para list)
    caps = agent.capabilities or {}
    if isinstance(caps, dict):
        caps_list = list(caps.keys()) if caps else []
    else:
        caps_list = list(caps) if caps else []
    
    return AgentRead(
        id=agent.id,
        tenant_id=agent.tenant_id,
        name=agent.name,
        machine_name=agent.machine_name,
        ip_address=agent.ip_address,
        version=agent.version,
        status=agent.status,
        last_heartbeat=agent.last_heartbeat,
        capabilities=caps_list,
        extra_data=agent.extra_data or {},
        is_online=is_online,
        created_at=agent.created_at,
        updated_at=agent.updated_at
    )


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post(
    "",
    response_model=AgentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Criar Agente",
    description="Cria novo agente RPA com validações."
)
async def create_agent(
    agent_data: AgentCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session)
) -> AgentRead:
    """Cria novo agente com validação de nome único por tenant"""
    service = AgentService(session)
    agent = await service.create_agent(tenant_id, agent_data)
    return _agent_to_read(agent)


@router.get(
    "",
    response_model=PaginatedResponse[AgentRead],
    status_code=status.HTTP_200_OK,
    summary="Listar Agentes",
    description="Lista agentes com filtros e paginação."
)
async def list_agents(
    tenant_id: UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: str = Query(None),
    capabilities: str = Query(None),
    machine_name: str = Query(None),
    is_active: bool = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc")
) -> PaginatedResponse[AgentRead]:
    """Lista agentes com filtros (status, capabilities, machine_name)"""
    filters = AgentFilterParams(
        page=page,
        size=size,
        status=status,
        capabilities=capabilities,
        machine_name=machine_name,
        is_active=is_active,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    service = AgentService(session)
    agents, total = await service.list_agents(tenant_id, filters)
    
    return PaginatedResponse.create(
        items=[_agent_to_read(agent) for agent in agents],
        total=total,
        params=filters
    )


@router.get(
    "/{agent_id}",
    response_model=AgentRead,
    status_code=status.HTTP_200_OK,
    summary="Detalhe do Agente",
    description="Retorna dados completos de um agente."
)
async def get_agent(
    agent_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session)
) -> AgentRead:
    """Busca agente por ID (validação de tenant)"""
    service = AgentService(session)
    agent = await service.get_agent(tenant_id, agent_id)
    return _agent_to_read(agent)


@router.put(
    "/{agent_id}",
    response_model=AgentRead,
    status_code=status.HTTP_200_OK,
    summary="Atualizar Agente",
    description="Atualiza dados do agente."
)
async def update_agent(
    agent_id: UUID,
    agent_data: AgentUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session)
) -> AgentRead:
    """Atualiza agente (campos opcionais)"""
    service = AgentService(session)
    agent = await service.update_agent(tenant_id, agent_id, agent_data)
    return _agent_to_read(agent)


@router.delete(
    "/{agent_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Deletar Agente",
    description="Soft delete de agente."
)
async def delete_agent(
    agent_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session)
) -> MessageResponse:
    """Soft delete: marca agente como deletado"""
    service = AgentService(session)
    await service.delete_agent(tenant_id, agent_id)
    
    return MessageResponse(message=f"Agente deletado com sucesso")


@router.post(
    "/{agent_id}/heartbeat",
    response_model=HeartbeatResponse,
    status_code=status.HTTP_200_OK,
    summary="Registrar Heartbeat",
    description="Registra heartbeat do agente."
)
async def record_heartbeat(
    agent_id: UUID,
    heartbeat_data: HeartbeatRequest,
    tenant_id: UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session)
) -> HeartbeatResponse:
    """Registra heartbeat (atualiza last_heartbeat e status)"""
    service = AgentService(session)
    agent = await service.record_heartbeat(
        tenant_id,
        agent_id,
        heartbeat_data
    )
    
    # Calcular is_online
    from datetime import datetime, timedelta
    is_online = False
    if agent.last_heartbeat:
        time_diff = datetime.utcnow() - agent.last_heartbeat.replace(tzinfo=None)
        is_online = time_diff < timedelta(minutes=5)
    
    return HeartbeatResponse(
        agent_id=agent.id,
        status=agent.status,
        last_heartbeat=agent.last_heartbeat or datetime.utcnow(),
        is_online=is_online,
        message="Heartbeat registrado com sucesso"
    )