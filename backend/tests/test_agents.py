"""
Tests para Agents CRUD endpoints.

Cobre:
- POST /agents (create)
- GET /agents (list com filtros)
- GET /agents/{id} (read)
- PUT /agents/{id} (update)
- DELETE /agents/{id} (delete/soft)
- POST /agents/{id}/heartbeat (heartbeat)
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient

from app.main import app
from app.models import User, Tenant, Agente
from app.core.security import hash_password
from app.schemas import AgentCreate, AgentUpdate, HeartbeatRequest


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
async def tenant(session: AsyncSession) -> Tenant:
    """Cria tenant de teste"""
    tenant = Tenant(
        id=uuid4(),
        name="Test Tenant",
        is_active=True
    )
    session.add(tenant)
    await session.commit()
    return tenant


@pytest.fixture
async def user(session: AsyncSession, tenant: Tenant) -> User:
    """Cria usuário de teste com tenant"""
    user = User(
        id=uuid4(),
        tenant_id=tenant.id,
        email="test@example.com",
        password_hash=hash_password("password123"),
        full_name="Test User",
        is_active=True
    )
    session.add(user)
    await session.commit()
    return user


@pytest.fixture
async def auth_headers(user: User) -> dict:
    """Gera headers com token de autenticação"""
    from app.core.security import create_access_token
    token = create_access_token(user_id=str(user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def agent(session: AsyncSession, tenant: Tenant) -> Agente:
    """Cria agente de teste"""
    agent = Agente(
        id=uuid4(),
        tenant_id=tenant.id,
        name="Test Agent 1",
        machine_name="machine-001",
        ip_address="192.168.1.1",
        version="1.0.0",
        status="offline",
        is_active=True,
        capabilities=["web", "excel"]
    )
    session.add(agent)
    await session.commit()
    return agent


# ============================================================================
# TESTS - CREATE
# ============================================================================

@pytest.mark.asyncio
async def test_create_agent_success(
    client: AsyncClient,
    auth_headers: dict
):
    """Criar agente com sucesso"""
    payload = {
        "name": "Agent Novo",
        "machine_name": "machine-002",
        "ip_address": "192.168.1.2",
        "version": "1.0.0",
        "capabilities": ["web"]
    }
    
    response = await client.post(
        "/api/v1/agents",
        json=payload,
        headers=auth_headers
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Agent Novo"
    assert data["machine_name"] == "machine-002"
    assert data["status"] == "offline"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_create_agent_duplicate_name(
    client: AsyncClient,
    auth_headers: dict,
    agent: Agente
):
    """Rejeitar agente com nome duplicado (mesmo tenant)"""
    payload = {
        "name": agent.name,  # Mesmo nome
        "machine_name": "machine-002",
        "version": "1.0.0",
        "capabilities": ["web"]
    }
    
    response = await client.post(
        "/api/v1/agents",
        json=payload,
        headers=auth_headers
    )
    
    assert response.status_code == 409  # Conflict
    assert "já existe" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_agent_missing_fields(
    client: AsyncClient,
    auth_headers: dict
):
    """Rejeitar agente com campos obrigatórios faltando"""
    payload = {
        "machine_name": "machine-002"
        # Faltam: name, version, capabilities
    }
    
    response = await client.post(
        "/api/v1/agents",
        json=payload,
        headers=auth_headers
    )
    
    assert response.status_code == 422  # Validation error


# ============================================================================
# TESTS - READ (LIST)
# ============================================================================

@pytest.mark.asyncio
async def test_list_agents_empty(
    client: AsyncClient,
    auth_headers: dict,
    user: User,
    session: AsyncSession
):
    """Listar agentes (empty)"""
    # Deletar todos os agentes do tenant
    from sqlalchemy import select
    stmt = select(Agente).where(Agente.tenant_id == user.tenant_id)
    result = await session.execute(stmt)
    for agent in result.scalars():
        await session.delete(agent)
    await session.commit()
    
    response = await client.get(
        "/api/v1/agents",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["items"]) == 0


@pytest.mark.asyncio
async def test_list_agents_with_pagination(
    client: AsyncClient,
    auth_headers: dict,
    agent: Agente,
    session: AsyncSession,
    tenant: Tenant
):
    """Listar agentes com paginação"""
    # Criar 5 agentes adicionais
    for i in range(5):
        a = Agente(
            tenant_id=tenant.id,
            name=f"Agent {i}",
            machine_name=f"machine-{i}",
            version="1.0.0",
            status="offline",
            is_active=True,
            capabilities=["web"]
        )
        session.add(a)
    await session.commit()
    
    # Page 1, size 3
    response = await client.get(
        "/api/v1/agents?page=1&size=3",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 6  # 5 + 1 from fixture
    assert len(data["items"]) == 3


@pytest.mark.asyncio
async def test_list_agents_filter_by_status(
    client: AsyncClient,
    auth_headers: dict,
    session: AsyncSession,
    tenant: Tenant
):
    """Listar agentes filtrando por status"""
    # Criar agentes com diferentes status
    online_agent = Agente(
        tenant_id=tenant.id,
        name="Online Agent",
        machine_name="machine-online",
        version="1.0.0",
        status="online",
        is_active=True,
        capabilities=["web"],
        last_heartbeat=datetime.utcnow()
    )
    
    offline_agent = Agente(
        tenant_id=tenant.id,
        name="Offline Agent",
        machine_name="machine-offline",
        version="1.0.0",
        status="offline",
        is_active=True,
        capabilities=["web"]
    )
    
    session.add(online_agent)
    session.add(offline_agent)
    await session.commit()
    
    # Filter by status=online
    response = await client.get(
        "/api/v1/agents?status=online",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["status"] == "online"


@pytest.mark.asyncio
async def test_list_agents_filter_by_machine_name(
    client: AsyncClient,
    auth_headers: dict,
    agent: Agente
):
    """Listar agentes filtrando por machine_name"""
    response = await client.get(
        f"/api/v1/agents?machine_name={agent.machine_name}",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    # Verificar que resultado contém machine_name
    assert any(a["machine_name"] == agent.machine_name for a in data["items"])


@pytest.mark.asyncio
async def test_list_agents_sort(
    client: AsyncClient,
    auth_headers: dict,
    session: AsyncSession,
    tenant: Tenant
):
    """Listar agentes com sorting"""
    # Criar agentes com nomes diferentes
    for name in ["Charlie", "Alice", "Bob"]:
        a = Agente(
            tenant_id=tenant.id,
            name=name,
            machine_name=f"machine-{name}",
            version="1.0.0",
            status="offline",
            is_active=True,
            capabilities=["web"]
        )
        session.add(a)
    await session.commit()
    
    # Sort by name asc
    response = await client.get(
        "/api/v1/agents?sort_by=name&sort_order=asc&size=100",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    names = [item["name"] for item in data["items"]]
    # Verificar se está ordenado
    assert names == sorted(names)


# ============================================================================
# TESTS - READ (GET)
# ============================================================================

@pytest.mark.asyncio
async def test_get_agent_success(
    client: AsyncClient,
    auth_headers: dict,
    agent: Agente
):
    """Buscar agente por ID"""
    response = await client.get(
        f"/api/v1/agents/{agent.id}",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(agent.id)
    assert data["name"] == agent.name
    assert data["tenant_id"] == str(agent.tenant_id)


@pytest.mark.asyncio
async def test_get_agent_not_found(
    client: AsyncClient,
    auth_headers: dict
):
    """Buscar agente inexistente"""
    fake_id = uuid4()
    response = await client.get(
        f"/api/v1/agents/{fake_id}",
        headers=auth_headers
    )
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_agent_wrong_tenant(
    client: AsyncClient,
    auth_headers: dict,
    session: AsyncSession
):
    """Rejeitar acesso a agente de outro tenant"""
    # Criar outro tenant e agente
    other_tenant = Tenant(id=uuid4(), name="Other", is_active=True)
    other_agent = Agente(
        id=uuid4(),
        tenant_id=other_tenant.id,
        name="Other Agent",
        machine_name="machine-other",
        version="1.0.0",
        status="offline",
        is_active=True
    )
    session.add(other_tenant)
    session.add(other_agent)
    await session.commit()
    
    # Tentar acessar com usuário de outro tenant
    response = await client.get(
        f"/api/v1/agents/{other_agent.id}",
        headers=auth_headers
    )
    
    assert response.status_code == 404  # Isolamento de tenant


# ============================================================================
# TESTS - UPDATE
# ============================================================================

@pytest.mark.asyncio
async def test_update_agent_success(
    client: AsyncClient,
    auth_headers: dict,
    agent: Agente
):
    """Atualizar agente com sucesso"""
    payload = {
        "name": "Updated Agent Name",
        "ip_address": "192.168.1.99",
        "is_active": False
    }
    
    response = await client.put(
        f"/api/v1/agents/{agent.id}",
        json=payload,
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Agent Name"
    assert data["ip_address"] == "192.168.1.99"
    assert data["is_active"] is False


@pytest.mark.asyncio
async def test_update_agent_duplicate_name(
    client: AsyncClient,
    auth_headers: dict,
    session: AsyncSession,
    tenant: Tenant,
    agent: Agente
):
    """Rejeitar mudança de nome para valor duplicado"""
    # Criar outro agente
    other = Agente(
        tenant_id=tenant.id,
        name="Other Name",
        machine_name="machine-other",
        version="1.0.0",
        status="offline",
        is_active=True
    )
    session.add(other)
    await session.commit()
    
    # Tentar mudare primeiro agente para nome do segundo
    payload = {"name": other.name}
    response = await client.put(
        f"/api/v1/agents/{agent.id}",
        json=payload,
        headers=auth_headers
    )
    
    assert response.status_code == 409  # Conflict


@pytest.mark.asyncio
async def test_update_agent_not_found(
    client: AsyncClient,
    auth_headers: dict
):
    """Atualizar agente inexistente"""
    fake_id = uuid4()
    payload = {"name": "New Name"}
    
    response = await client.put(
        f"/api/v1/agents/{fake_id}",
        json=payload,
        headers=auth_headers
    )
    
    assert response.status_code == 404


# ============================================================================
# TESTS - DELETE
# ============================================================================

@pytest.mark.asyncio
async def test_delete_agent_success(
    client: AsyncClient,
    auth_headers: dict,
    agent: Agente
):
    """Deletar agente (soft delete)"""
    response = await client.delete(
        f"/api/v1/agents/{agent.id}",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    assert "sucesso" in response.json()["message"].lower()


@pytest.mark.asyncio
async def test_delete_agent_not_found(
    client: AsyncClient,
    auth_headers: dict
):
    """Deletar agente inexistente"""
    fake_id = uuid4()
    response = await client.delete(
        f"/api/v1/agents/{fake_id}",
        headers=auth_headers
    )
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_deleted_agent_not_in_list(
    client: AsyncClient,
    auth_headers: dict,
    agent: Agente
):
    """Agente deletado não deve aparecer na lista"""
    # Deletar
    response = await client.delete(
        f"/api/v1/agents/{agent.id}",
        headers=auth_headers
    )
    assert response.status_code == 200
    
    # Listar
    response = await client.get(
        "/api/v1/agents",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    # Agente deletado não deve estar na lista
    assert not any(a["id"] == str(agent.id) for a in data["items"])


# ============================================================================
# TESTS - HEARTBEAT
# ============================================================================

@pytest.mark.asyncio
async def test_record_heartbeat_success(
    client: AsyncClient,
    auth_headers: dict,
    agent: Agente
):
    """Registrar heartbeat com sucesso"""
    payload = {
        "status": "online",
        "extra_data": {
            "cpu_usage": 45.2,
            "memory_usage": 62.1
        }
    }
    
    response = await client.post(
        f"/api/v1/agents/{agent.id}/heartbeat",
        json=payload,
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "last_heartbeat" in data


@pytest.mark.asyncio
async def test_record_heartbeat_updates_timestamp(
    client: AsyncClient,
    auth_headers: dict,
    agent: Agente,
    session: AsyncSession
):
    """Heartbeat deve atualizar last_heartbeat"""
    # Record heartbeat
    payload = {"status": "busy"}
    response = await client.post(
        f"/api/v1/agents/{agent.id}/heartbeat",
        json=payload,
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Timestamp deve ser recente
    heartbeat_time = datetime.fromisoformat(data["last_heartbeat"].replace("Z", "+00:00"))
    now = datetime.utcnow()
    diff = now - heartbeat_time.replace(tzinfo=None)
    assert diff < timedelta(seconds=5)


@pytest.mark.asyncio
async def test_record_heartbeat_not_found(
    client: AsyncClient,
    auth_headers: dict
):
    """Heartbeat para agente inexistente"""
    fake_id = uuid4()
    payload = {"status": "online"}
    
    response = await client.post(
        f"/api/v1/agents/{fake_id}/heartbeat",
        json=payload,
        headers=auth_headers
    )
    
    assert response.status_code == 404


# ============================================================================
# TESTS - AUTHORIZATION
# ============================================================================

@pytest.mark.asyncio
async def test_agent_endpoints_require_auth(
    client: AsyncClient,
    agent: Agente
):
    """Endpoints de agent devem requer autenticação"""
    endpoints = [
        ("GET", f"/api/v1/agents"),
        ("POST", f"/api/v1/agents"),
        ("GET", f"/api/v1/agents/{agent.id}"),
        ("PUT", f"/api/v1/agents/{agent.id}"),
        ("DELETE", f"/api/v1/agents/{agent.id}"),
        ("POST", f"/api/v1/agents/{agent.id}/heartbeat"),
    ]
    
    for method, endpoint in endpoints:
        if method == "GET":
            response = await client.get(endpoint)
        elif method == "POST":
            response = await client.post(endpoint, json={})
        elif method == "PUT":
            response = await client.put(endpoint, json={})
        elif method == "DELETE":
            response = await client.delete(endpoint)
        
        assert response.status_code == 401  # Unauthorized
