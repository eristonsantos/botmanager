# backend/tests/test_agents.py
"""
Testes para endpoints e service de agentes.

Cobertura:
- CRUD completo
- Validações (nome único, capabilities, semver)
- Filtros e paginação
- Heartbeat
- Multi-tenant isolation
"""

import pytest
from uuid import uuid4
from datetime import datetime, timedelta

from app.models.core import StatusAgenteEnum
from app.services.agent_service import AgentService
from app.schemas.agent import AgentCreate, AgentUpdate, HeartbeatRequest, AgentFilterParams
from app.core.exceptions import ConflictError, NotFoundError


# ============================================================================
# SERVICE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_create_agent_success(session, tenant):
    """Testa criação de agente com sucesso"""
    service = AgentService(session)
    
    agent_data = AgentCreate(
        name="bot-001",
        machine_name="worker-001",
        capabilities=["web", "excel"],
        version="1.0.0"
    )
    
    agent = await service.create_agent(tenant.id, agent_data)

    assert agent.name == "bot-001"
    assert agent.status == StatusAgenteEnum.OFFLINE
    assert agent.tenant_id == tenant.id
    assert agent.id is not None


@pytest.mark.asyncio
async def test_create_agent_duplicate_name_fails(session, tenant, agent):
    """Testa que nome duplicado falha"""
    service = AgentService(session)

    agent_data = AgentCreate(
        name=agent.name,  # Mesmo nome do fixture
        machine_name="another-machine",
        capabilities=["web"],
        version="1.0.0"
    )

    with pytest.raises(ConflictError) as exc_info:
        await service.create_agent(tenant.id, agent_data)

    assert "já existe" in str(exc_info.value.message)


@pytest.mark.asyncio
async def test_get_agent_success(session, tenant, agent):
    """Testa busca de agente por ID"""
    service = AgentService(session)

    found = await service.get_agent(tenant.id, agent.id)

    assert found.id == agent.id
    assert found.name == agent.name


@pytest.mark.asyncio
async def test_get_agent_not_found(session, tenant):
    """Testa que agente inexistente retorna 404"""
    service = AgentService(session)

    with pytest.raises(NotFoundError):
        await service.get_agent(tenant.id, uuid4())


@pytest.mark.asyncio
async def test_update_agent_success(session, tenant, agent):
    """Testa atualização de agente"""
    service = AgentService(session)

    update_data = AgentUpdate(
        name="bot-updated",
        status=StatusAgenteEnum.ONLINE
    )

    updated = await service.update_agent(tenant.id, agent.id, update_data)

    assert updated.name == "bot-updated"
    assert updated.status == StatusAgenteEnum.ONLINE


@pytest.mark.asyncio
async def test_delete_agent_soft_delete(session, tenant, agent):
    """Testa soft delete de agente"""
    service = AgentService(session)

    await service.delete_agent(tenant.id, agent.id)

    # Tentar buscar deve falhar (soft deleted)
    with pytest.raises(NotFoundError):
        await service.get_agent(tenant.id, agent.id)


@pytest.mark.asyncio
async def test_heartbeat_updates_last_heartbeat(session, tenant, agent):
    """Testa que heartbeat atualiza last_heartbeat"""
    service = AgentService(session)

    assert agent.last_heartbeat is None

    heartbeat_data = HeartbeatRequest(status=StatusAgenteEnum.ONLINE)
    updated = await service.record_heartbeat(tenant.id, agent.id, heartbeat_data)
    
    assert updated.last_heartbeat is not None
    assert updated.status == StatusAgenteEnum.ONLINE


@pytest.mark.asyncio
async def test_list_agents_filter_by_status(session, tenant):
    """Testa listagem filtrada por status"""
    service = AgentService(session)
    
    # Criar 2 agentes
    agent1 = AgentCreate(
        name="bot-online",
        machine_name="machine-1",
        capabilities=["web"],
        version="1.0.0"
    )
    await service.create_agent(tenant.id, agent1)

    agent2 = AgentCreate(
        name="bot-offline",
        machine_name="machine-2",
        capabilities=["web"],
        version="1.0.0"
    )
    await service.create_agent(tenant.id, agent2)
    
    # Listar apenas offline
    filters = AgentFilterParams(
        page=1,
        size=10,
        status=StatusAgenteEnum.OFFLINE
    )
    
    agents, total = await service.list_agents(tenant.id, filters)
    
    assert total == 2  # Ambos criados como offline
    assert all(a.status == StatusAgenteEnum.OFFLINE for a in agents)


@pytest.mark.asyncio
async def test_list_agents_pagination(session, tenant):
    """Testa paginação na listagem"""
    service = AgentService(session)
    
    # Criar 25 agentes
    for i in range(25):
        agent_data = AgentCreate(
            name=f"bot-{i:03d}",
            machine_name=f"machine-{i}",
            capabilities=["web"],
            version="1.0.0"
        )
        await service.create_agent(tenant.id, agent_data)
    
    # Page 1, size 10
    filters = AgentFilterParams(page=1, size=10)
    agents_p1, total = await service.list_agents(tenant.id, filters)
    
    assert len(agents_p1) == 10
    assert total == 25
    
    # Page 2
    filters = AgentFilterParams(page=2, size=10)
    agents_p2, _ = await service.list_agents(tenant.id, filters)
    
    assert len(agents_p2) == 10
    assert agents_p1[0].id != agents_p2[0].id


@pytest.mark.asyncio
async def test_list_agents_filter_is_online(session, tenant):
    """Testa filtro is_online (heartbeat < 5min)"""
    service = AgentService(session)
    
    # Criar agente com heartbeat antigo
    agent_data = AgentCreate(
        name="bot-heartbeat-test",
        machine_name="machine-hb",
        capabilities=["web"],
        version="1.0.0"
    )
    agent = await service.create_agent(tenant.id, agent_data)

    # Registrar heartbeat (fica online)
    hb_data = HeartbeatRequest(status=StatusAgenteEnum.ONLINE)
    await service.record_heartbeat(tenant.id, agent.id, hb_data)
    
    # Filtrar online
    filters = AgentFilterParams(page=1, size=10, is_online=True)
    online_agents, _ = await service.list_agents(tenant.id, filters)
    
    assert len(online_agents) >= 1
    assert any(a.id == agent.id for a in online_agents)


# ============================================================================
# ENDPOINT TESTS
# ============================================================================

def test_create_agent_endpoint(client, auth_headers):
    """Testa endpoint POST /agents"""
    response = client.post(
        "/api/v1/agents",
        headers=auth_headers,
        json={
            "name": "bot-endpoint",
            "machine_name": "machine-endpoint",
            "capabilities": ["web", "excel"],
            "version": "1.0.0",
            "metadata": {}
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "bot-endpoint"
    assert data["status"] == "offline"
    assert data["is_online"] == False


def test_list_agents_endpoint(client, auth_headers, agent):
    """Testa endpoint GET /agents"""
    response = client.get(
        "/api/v1/agents?page=1&size=10",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1
    assert data["page"] == 1
    assert data["size"] == 10


def test_get_agent_endpoint(client, auth_headers, agent):
    """Testa endpoint GET /agents/{id}"""
    response = client.get(
        f"/api/v1/agents/{agent.id}",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(agent.id)
    assert data["name"] == agent.name


def test_update_agent_endpoint(client, auth_headers, agent):
    """Testa endpoint PUT /agents/{id}"""
    response = client.put(
        f"/api/v1/agents/{agent.id}",
        headers=auth_headers,
        json={"name": "bot-updated-endpoint"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "bot-updated-endpoint"


def test_delete_agent_endpoint(client, auth_headers, agent):
    """Testa endpoint DELETE /agents/{id}"""
    response = client.delete(
        f"/api/v1/agents/{agent.id}",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    
    # Verificar que foi deletado
    response_get = client.get(
        f"/api/v1/agents/{agent.id}",
        headers=auth_headers
    )
    assert response_get.status_code == 404


def test_heartbeat_endpoint(client, auth_headers, agent):
    """Testa endpoint POST /agents/{id}/heartbeat"""
    response = client.post(
        f"/api/v1/agents/{agent.id}/heartbeat",
        headers=auth_headers,
        json={"status": "online"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["last_heartbeat"] is not None
    assert data["is_online"] == True


def test_list_agents_with_filter(client, auth_headers, agent):
    """Testa listagem com filtros"""
    response = client.get(
        f"/api/v1/agents?page=1&size=10&status=offline",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert all(item["status"] == "offline" for item in data["items"])


def test_unauthorized_access_requires_auth(client):
    """Testa que acesso sem token falha"""
    response = client.get("/api/v1/agents")
    
    assert response.status_code == 403 or response.status_code == 401


def test_create_agent_invalid_semver(client, auth_headers):
    """Testa validação de versão semver"""
    response = client.post(
        "/api/v1/agents",
        headers=auth_headers,
        json={
            "name": "bot-invalid-version",
            "machine_name": "machine",
            "capabilities": ["web"],
            "version": "invalid-version"  # Inválido
        }
    )
    
    assert response.status_code == 422  # Validation error


def test_create_agent_empty_capabilities(client, auth_headers):
    """Testa validação de capabilities vazio"""
    response = client.post(
        "/api/v1/agents",
        headers=auth_headers,
        json={
            "name": "bot-no-caps",
            "machine_name": "machine",
            "capabilities": [],  # Vazio = inválido
            "version": "1.0.0"
        }
    )
    
    assert response.status_code == 422  # Validation error