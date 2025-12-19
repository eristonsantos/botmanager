"""
Comprehensive Tenant Integration Tests

Tests multi-tenancy functionality including:
- Tenant CRUD operations
- User registration within tenants
- Multi-tenant data isolation
- Authentication with tenant context
- Cross-tenant access prevention
"""

import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.tenant import Tenant, User
from app.models.core import Agente
from app.core.security import hash_password, verify_password


# ============================================================================
# TENANT MODEL TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_create_tenant_success(session: AsyncSession):
    """Test creating a tenant successfully"""
    tenant = Tenant(
        id=uuid4(),
        name="Acme Corporation",
        slug="acme-corp",
        is_active=True,
        settings={"timezone": "UTC", "language": "en"}
    )

    session.add(tenant)
    await session.commit()
    await session.refresh(tenant)

    assert tenant.id is not None
    assert tenant.name == "Acme Corporation"
    assert tenant.slug == "acme-corp"
    assert tenant.is_active is True
    assert tenant.settings["timezone"] == "UTC"


@pytest.mark.asyncio
async def test_tenant_slug_unique_constraint(session: AsyncSession):
    """Test that tenant slugs must be unique"""
    tenant1 = Tenant(
        id=uuid4(),
        name="Company One",
        slug="same-slug",
        is_active=True
    )

    session.add(tenant1)
    await session.commit()

    # Try to create another tenant with same slug
    tenant2 = Tenant(
        id=uuid4(),
        name="Company Two",
        slug="same-slug",  # Same slug
        is_active=True
    )

    session.add(tenant2)

    with pytest.raises(Exception):  # Should raise IntegrityError
        await session.commit()


@pytest.mark.asyncio
async def test_tenant_name_unique_constraint(session: AsyncSession):
    """Test that tenant names must be unique"""
    tenant1 = Tenant(
        id=uuid4(),
        name="Unique Name",
        slug="slug-1",
        is_active=True
    )

    session.add(tenant1)
    await session.commit()

    # Try to create another tenant with same name
    tenant2 = Tenant(
        id=uuid4(),
        name="Unique Name",  # Same name
        slug="slug-2",
        is_active=True
    )

    session.add(tenant2)

    with pytest.raises(Exception):  # Should raise IntegrityError
        await session.commit()


@pytest.mark.asyncio
async def test_tenant_deactivation(session: AsyncSession):
    """Test deactivating a tenant"""
    tenant = Tenant(
        id=uuid4(),
        name="Test Deactivation",
        slug="test-deactivation",
        is_active=True
    )

    session.add(tenant)
    await session.commit()

    # Deactivate tenant
    tenant.is_active = False
    await session.commit()
    await session.refresh(tenant)

    assert tenant.is_active is False


# ============================================================================
# USER-TENANT RELATIONSHIP TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_create_user_with_tenant(session: AsyncSession, tenant: Tenant):
    """Test creating a user associated with a tenant"""
    user = User(
        id=uuid4(),
        tenant_id=tenant.id,
        email="user@example.com",
        hashed_password=hash_password("SecurePass123!"),
        full_name="Test User",
        is_active=True,
        is_superuser=False
    )

    session.add(user)
    await session.commit()
    await session.refresh(user)

    assert user.id is not None
    assert user.tenant_id == tenant.id
    assert user.email == "user@example.com"
    assert verify_password("SecurePass123!", user.hashed_password)


@pytest.mark.asyncio
async def test_user_email_unique_per_tenant(session: AsyncSession):
    """Test that email is unique within a tenant"""
    # Create two tenants
    tenant1 = Tenant(id=uuid4(), name="Tenant 1", slug="tenant-1", is_active=True)
    tenant2 = Tenant(id=uuid4(), name="Tenant 2", slug="tenant-2", is_active=True)
    session.add(tenant1)
    session.add(tenant2)
    await session.commit()

    # Create user in tenant1
    user1 = User(
        id=uuid4(),
        tenant_id=tenant1.id,
        email="same@example.com",
        hashed_password=hash_password("Pass123!"),
        full_name="User 1",
        is_active=True
    )
    session.add(user1)
    await session.commit()

    # Try to create another user with same email in same tenant
    user2 = User(
        id=uuid4(),
        tenant_id=tenant1.id,
        email="same@example.com",  # Same email, same tenant
        hashed_password=hash_password("Pass123!"),
        full_name="User 2",
        is_active=True
    )
    session.add(user2)

    with pytest.raises(Exception):  # Should raise IntegrityError
        await session.commit()

    await session.rollback()

    # Refresh tenant2 after rollback to avoid detached instance error
    await session.refresh(tenant2)

    # But same email in different tenant should work
    user3 = User(
        id=uuid4(),
        tenant_id=tenant2.id,
        email="same@example.com",  # Same email, different tenant
        hashed_password=hash_password("Pass123!"),
        full_name="User 3",
        is_active=True
    )
    session.add(user3)
    await session.commit()
    await session.refresh(user3)

    assert user3.email == "same@example.com"
    assert user3.tenant_id == tenant2.id


@pytest.mark.asyncio
async def test_user_soft_delete(session: AsyncSession, user: User):
    """Test soft deleting a user"""
    from datetime import datetime

    # Soft delete user
    user.deleted_at = datetime.utcnow()
    await session.commit()
    await session.refresh(user)

    assert user.deleted_at is not None


@pytest.mark.asyncio
async def test_tenant_user_relationship(session: AsyncSession, tenant: Tenant):
    """Test the relationship between tenant and users"""
    # Create multiple users for the tenant
    users = []
    for i in range(3):
        user = User(
            id=uuid4(),
            tenant_id=tenant.id,
            email=f"user{i}@example.com",
            hashed_password=hash_password("Pass123!"),
            full_name=f"User {i}",
            is_active=True
        )
        session.add(user)
        users.append(user)

    await session.commit()

    # Refresh tenant to load relationship
    await session.refresh(tenant)

    # Check relationship
    assert len(tenant.users) >= 3


# ============================================================================
# MULTI-TENANT DATA ISOLATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_multi_tenant_agent_isolation(session: AsyncSession):
    """Test that agents are isolated between tenants"""
    # Create two tenants
    tenant1 = Tenant(id=uuid4(), name="Tenant 1", slug="tenant-1", is_active=True)
    tenant2 = Tenant(id=uuid4(), name="Tenant 2", slug="tenant-2", is_active=True)
    session.add(tenant1)
    session.add(tenant2)
    await session.commit()

    # Create agent for tenant1
    agent1 = Agente(
        id=uuid4(),
        tenant_id=tenant1.id,
        name="Agent Tenant 1",
        machine_name="machine-1",
        version="1.0.0",
        status="offline",
        is_active=True,
        capabilities=["web"]
    )

    # Create agent for tenant2
    agent2 = Agente(
        id=uuid4(),
        tenant_id=tenant2.id,
        name="Agent Tenant 2",
        machine_name="machine-2",
        version="1.0.0",
        status="offline",
        is_active=True,
        capabilities=["web"]
    )

    session.add(agent1)
    session.add(agent2)
    await session.commit()

    # Query agents for tenant1
    stmt = select(Agente).where(
        Agente.tenant_id == tenant1.id,
        Agente.deleted_at.is_(None)
    )
    result = await session.execute(stmt)
    tenant1_agents = result.scalars().all()

    # Should only see tenant1's agent
    assert len(tenant1_agents) == 1
    assert tenant1_agents[0].id == agent1.id
    assert tenant1_agents[0].name == "Agent Tenant 1"

    # Query agents for tenant2
    stmt = select(Agente).where(
        Agente.tenant_id == tenant2.id,
        Agente.deleted_at.is_(None)
    )
    result = await session.execute(stmt)
    tenant2_agents = result.scalars().all()

    # Should only see tenant2's agent
    assert len(tenant2_agents) == 1
    assert tenant2_agents[0].id == agent2.id
    assert tenant2_agents[0].name == "Agent Tenant 2"


@pytest.mark.asyncio
async def test_prevent_cross_tenant_user_access(session: AsyncSession):
    """Test that users cannot see users from other tenants"""
    # Create two tenants
    tenant1 = Tenant(id=uuid4(), name="Tenant 1", slug="tenant-1", is_active=True)
    tenant2 = Tenant(id=uuid4(), name="Tenant 2", slug="tenant-2", is_active=True)
    session.add(tenant1)
    session.add(tenant2)
    await session.commit()

    # Create users for each tenant
    user1 = User(
        id=uuid4(),
        tenant_id=tenant1.id,
        email="user1@tenant1.com",
        hashed_password=hash_password("Pass123!"),
        full_name="User 1",
        is_active=True
    )

    user2 = User(
        id=uuid4(),
        tenant_id=tenant2.id,
        email="user2@tenant2.com",
        hashed_password=hash_password("Pass123!"),
        full_name="User 2",
        is_active=True
    )

    session.add(user1)
    session.add(user2)
    await session.commit()

    # Query users for tenant1
    stmt = select(User).where(
        User.tenant_id == tenant1.id,
        User.deleted_at.is_(None)
    )
    result = await session.execute(stmt)
    tenant1_users = result.scalars().all()

    # Should only see tenant1's user
    assert len(tenant1_users) == 1
    assert tenant1_users[0].email == "user1@tenant1.com"

    # Verify user2 is NOT in tenant1 results
    tenant1_user_ids = [u.id for u in tenant1_users]
    assert user2.id not in tenant1_user_ids


@pytest.mark.asyncio
async def test_agents_with_same_name_different_tenants(session: AsyncSession):
    """Test that different tenants can have agents with the same name"""
    # Create two tenants
    tenant1 = Tenant(id=uuid4(), name="Tenant 1", slug="tenant-1", is_active=True)
    tenant2 = Tenant(id=uuid4(), name="Tenant 2", slug="tenant-2", is_active=True)
    session.add(tenant1)
    session.add(tenant2)
    await session.commit()

    # Create agents with same name in different tenants
    agent1 = Agente(
        id=uuid4(),
        tenant_id=tenant1.id,
        name="Production Bot",  # Same name
        machine_name="machine-1",
        version="1.0.0",
        status="offline",
        is_active=True,
        capabilities=["web"]
    )

    agent2 = Agente(
        id=uuid4(),
        tenant_id=tenant2.id,
        name="Production Bot",  # Same name
        machine_name="machine-2",
        version="1.0.0",
        status="offline",
        is_active=True,
        capabilities=["web"]
    )

    session.add(agent1)
    session.add(agent2)
    await session.commit()

    # Both should exist
    stmt = select(Agente).where(Agente.name == "Production Bot")
    result = await session.execute(stmt)
    agents = result.scalars().all()

    assert len(agents) == 2
    assert {a.tenant_id for a in agents} == {tenant1.id, tenant2.id}


# ============================================================================
# TENANT SETTINGS TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_tenant_custom_settings(session: AsyncSession):
    """Test storing and retrieving custom tenant settings"""
    custom_settings = {
        "timezone": "America/New_York",
        "language": "en-US",
        "features": {
            "automation_enabled": True,
            "max_concurrent_executions": 10,
            "notification_email": "admin@example.com"
        },
        "integrations": {
            "slack_webhook": "https://hooks.slack.com/services/XXX",
            "email_provider": "sendgrid"
        }
    }

    tenant = Tenant(
        id=uuid4(),
        name="Custom Settings Tenant",
        slug="custom-settings",
        is_active=True,
        settings=custom_settings
    )

    session.add(tenant)
    await session.commit()
    await session.refresh(tenant)

    # Verify settings are stored correctly
    assert tenant.settings["timezone"] == "America/New_York"
    assert tenant.settings["features"]["max_concurrent_executions"] == 10
    assert tenant.settings["integrations"]["slack_webhook"] == "https://hooks.slack.com/services/XXX"


@pytest.mark.asyncio
async def test_update_tenant_settings(session: AsyncSession, tenant: Tenant):
    """Test updating tenant settings"""
    # Initial settings
    tenant.settings = {"feature_a": True, "feature_b": False}
    await session.commit()

    # Update settings - need to create new dict for SQLAlchemy to detect changes
    new_settings = tenant.settings.copy()
    new_settings["feature_b"] = True
    new_settings["feature_c"] = "new_value"
    tenant.settings = new_settings
    await session.commit()
    await session.refresh(tenant)

    # Verify updates
    assert tenant.settings["feature_a"] is True
    assert tenant.settings["feature_b"] is True
    assert tenant.settings["feature_c"] == "new_value"


# ============================================================================
# TENANT QUERY FILTERS TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_query_only_active_tenants(session: AsyncSession):
    """Test querying only active tenants"""
    # Create active and inactive tenants
    active_tenant = Tenant(
        id=uuid4(),
        name="Active Tenant",
        slug="active",
        is_active=True
    )

    inactive_tenant = Tenant(
        id=uuid4(),
        name="Inactive Tenant",
        slug="inactive",
        is_active=False
    )

    session.add(active_tenant)
    session.add(inactive_tenant)
    await session.commit()

    # Query only active tenants
    stmt = select(Tenant).where(Tenant.is_active == True)
    result = await session.execute(stmt)
    active_tenants = result.scalars().all()

    # Should include active but not inactive
    active_tenant_ids = [t.id for t in active_tenants]
    assert active_tenant.id in active_tenant_ids
    assert inactive_tenant.id not in active_tenant_ids


@pytest.mark.asyncio
async def test_find_tenant_by_slug(session: AsyncSession):
    """Test finding tenant by slug"""
    tenant = Tenant(
        id=uuid4(),
        name="Find Me",
        slug="find-me-slug",
        is_active=True
    )

    session.add(tenant)
    await session.commit()

    # Find by slug
    stmt = select(Tenant).where(Tenant.slug == "find-me-slug")
    result = await session.execute(stmt)
    found_tenant = result.scalar_one_or_none()

    assert found_tenant is not None
    assert found_tenant.id == tenant.id
    assert found_tenant.name == "Find Me"


@pytest.mark.asyncio
async def test_count_users_per_tenant(session: AsyncSession):
    """Test counting users per tenant"""
    # Create tenant
    tenant = Tenant(id=uuid4(), name="User Count Test", slug="user-count", is_active=True)
    session.add(tenant)
    await session.commit()

    # Create multiple users
    for i in range(5):
        user = User(
            id=uuid4(),
            tenant_id=tenant.id,
            email=f"user{i}@test.com",
            hashed_password=hash_password("Pass123!"),
            full_name=f"User {i}",
            is_active=True
        )
        session.add(user)

    await session.commit()

    # Count users for tenant
    stmt = select(User).where(
        User.tenant_id == tenant.id,
        User.deleted_at.is_(None)
    )
    result = await session.execute(stmt)
    users = result.scalars().all()

    assert len(users) == 5
