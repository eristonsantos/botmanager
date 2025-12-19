#!/usr/bin/env python3
"""Seed data simplificado."""

import sys
import asyncio
from pathlib import Path
from datetime import datetime
from uuid import uuid4

# Adiciona backend ao path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Carrega .env
from dotenv import load_dotenv
env_path = backend_dir / ".env"
print(f"🔧 Carregando .env: {env_path}")
print(f"✅ .env existe: {env_path.exists()}")
load_dotenv(dotenv_path=env_path)

# Imports
from app.core.database import get_session_context
from app.core.security import hash_password
from app.models import Tenant, User

async def seed():
    print("\n🌱 Criando dados básicos...")
    
    async with get_session_context() as session:
        # Tenant
        tenant = Tenant(
            id=uuid4(),
            name="Demo Corp",
            slug="demo-corp",
            is_active=True,
            settings={}
        )
        session.add(tenant)
        await session.flush()
        print(f"✅ Tenant: {tenant.name}")
        
        # User
        user = User(
            id=uuid4(),
            tenant_id=tenant.id,
            email="admin@democorp.com",
            hashed_password=hash_password("Admin123!"),
            full_name="Admin Demo",
            is_active=True,
            is_superuser=True
        )
        session.add(user)
        await session.flush()
        print(f"✅ User: {user.email}")
        
        await session.commit()
        print("\n🎉 Sucesso!")

if __name__ == "__main__":
    asyncio.run(seed())
