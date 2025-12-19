# backend/tests/conftest.py
"""
Fixtures compartilhadas para testes.

Configuração:
- Banco de dados de teste (SQLite in-memory)
- Session assíncrona
- Cliente HTTP FastAPI
- Fixtures de autenticação
"""

import pytest
import pytest_asyncio
from typing import AsyncGenerator
from uuid import uuid4

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_session
from app.core.security import create_tokens_for_user, hash_password
from app.models.tenant import Tenant, User
from app.models.core import Agente, StatusAgenteEnum


# ============================================================================
# DATABASE FIXTURES
# ============================================================================

@pytest_asyncio.fixture
async def async_engine():
    """Cria engine para banco de teste (SQLite in-memory)"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    
    yield engine
    
    await engine.dispose()


@pytest_asyncio.fixture
async def session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Cria session assíncrona para testes"""
    async_session = sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session


@pytest.fixture
def client(session):
    """Cliente HTTP para testar endpoints"""
    
    def override_get_session():
        return session
    
    app.dependency_overrides[get_session] = override_get_session
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


# ============================================================================
# DATA FIXTURES
# ============================================================================

@pytest_asyncio.fixture
async def tenant(session: AsyncSession) -> Tenant:
    """Cria tenant de teste"""
    tenant = Tenant(
        id=uuid4(),
        name="Test Corp",
        slug="test-corp",
        is_active=True
    )
    session.add(tenant)
    await session.commit()
    await session.refresh(tenant)
    return tenant


@pytest_asyncio.fixture
async def user(session: AsyncSession, tenant: Tenant) -> User:
    """Cria usuário de teste"""
    user = User(
        id=uuid4(),
        tenant_id=tenant.id,
        email="test@test.com",
        hashed_password=hash_password("Test@123"),
        full_name="Test User",
        is_active=True,
        is_superuser=False
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture
async def agent(session: AsyncSession, tenant: Tenant) -> Agente:
    """Cria agente de teste"""
    agent = Agente(
        id=uuid4(),
        tenant_id=tenant.id,
        name="test-agent",
        machine_name="test-machine",
        status=StatusAgenteEnum.OFFLINE,
        capabilities=["web", "excel"],
        version="1.0.0"
    )
    session.add(agent)
    await session.commit()
    await session.refresh(agent)
    return agent


# ============================================================================
# AUTH FIXTURES
# ============================================================================

@pytest.fixture
def auth_token(user: User, tenant: Tenant) -> str:
    """Gera token JWT para autenticação"""
    tokens = create_tokens_for_user(
        user_id=str(user.id),
        tenant_id=str(tenant.id),
        additional_claims={"email": user.email}
    )
    return tokens["access_token"]


@pytest.fixture
def auth_headers(auth_token: str) -> dict:
    """Headers com autenticação"""
    return {"Authorization": f"Bearer {auth_token}"}