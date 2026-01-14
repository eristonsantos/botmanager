#!/usr/bin/env python3
"""
Script de seed data FINAL - Popula o ecossistema completo.
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from uuid import uuid4

# Configura o Path para encontrar os módulos do backend
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Importa as variáveis de ambiente (para carregar a ENCRYPTION_KEY)
from dotenv import load_dotenv
load_dotenv()

from app.core.database import get_session_context
# Ajuste de import: geralmente o hash está no init ou security.py base
try:
    from app.core.security import hash_password
except ImportError:
    from app.core.security import get_password_hash as hash_password

from app.core.security.encryption import encrypt_credential
from app.models import (
    Tenant, User, Agente, Processo, VersaoProcesso, 
    Asset, Credencial, Agendamento,
    StatusAgenteEnum, TipoProcessoEnum, 
    TipoAssetEnum, ScopeAssetEnum, TipoCredencialEnum
)

async def main():
    print("=" * 70)
    print("  🌱 SEED DATA - RPA ENTERPRISE")
    print("=" * 70)
    
    async with get_session_context() as session:
        # 1. CRIAR TENANT
        print("\n🏢 Criando Tenant...")
        tenant = Tenant(
            id=uuid4(),
            name="Cognit X Corp",
            slug="cognit-x",
            is_active=True,
            settings={"timezone": "America/Sao_Paulo"}
        )
        session.add(tenant)
        await session.flush() # Gera o ID do tenant para usarmos abaixo
        print(f"   ✅ Tenant criado: {tenant.name}")

        # 2. CRIAR USUÁRIO ADMIN (Humano)
        print("\n👤 Criando Usuários...")
        admin = User(
            id=uuid4(),
            tenant_id=tenant.id,
            email="admin@cognit.com",
            hashed_password=hash_password("Admin123!"),
            full_name="Administrador do Sistema",
            is_active=True,
            is_superuser=True
        )
        session.add(admin)

        # 3. CRIAR USUÁRIO DO ROBÔ (Para o Worker não quebrar)
        robot_user = User(
            id=uuid4(),
            tenant_id=tenant.id,
            email="robot01@example.com", # O email que seu main.py usa
            hashed_password=hash_password("robot_password_123"),
            full_name="Robô Worker 01",
            is_active=True,
            is_superuser=False
        )
        session.add(robot_user)
        print(f"   ✅ Usuário Admin: admin@cognit.com")
        print(f"   ✅ Usuário Robô: robot01@example.com (Compatível com Worker)")

        # 4. CRIAR PROCESSO DE EXEMPLO
        print("\n⚙️  Criando Processos...")
        proc = Processo(
            id=uuid4(),
            tenant_id=tenant.id,
            name="demo-process", # Nome usado na fila
            description="Processo de Demonstração RPA",
            tipo=TipoProcessoEnum.UNATTENDED,
            is_active=True,
            tags=["demo", "python"]
        )
        session.add(proc)
        await session.flush()
        print(f"   ✅ Processo: {proc.name}")

        # 5. CRIAR ASSETS (Configurações)
        print("\n📦 Criando Assets (Governance)...")
        asset_url = Asset(
            tenant_id=tenant.id,
            name="URL_ALVO",
            tipo=TipoAssetEnum.STRING,
            value="https://www.google.com",
            description="URL que o robô deve acessar",
            scope=ScopeAssetEnum.GLOBAL
        )
        session.add(asset_url)
        print(f"   ✅ Asset: URL_ALVO")

        # 6. CRIAR CREDENCIAL (Vault)
        print("\n🔐 Criando Credenciais (Vault)...")
        cred = Credencial(
            tenant_id=tenant.id,
            name="SAP_PROD",
            tipo=TipoCredencialEnum.BASIC_AUTH,
            username="bot_user",
            encrypted_password=encrypt_credential("SenhaSuperSecreta123!"), # Criptografa agora
            description="Acesso ao SAP Produção"
        )
        session.add(cred)
        print(f"   ✅ Credencial: SAP_PROD")

        # 7. CRIAR AGENDAMENTO
        print("\n📅 Criando Agendamento...")
        schedule = Agendamento(
            tenant_id=tenant.id,
            processo_id=proc.id,
            name="Execução Diária Matinal",
            cron_expression="0 8 * * 1-5", # Seg-Sex as 08:00
            is_active=True
        )
        session.add(schedule)
        print(f"   ✅ Agendamento: 08:00 Seg-Sex")

        await session.commit()
        
    print("\n" + "=" * 70)
    print("  🚀 SEED CONCLUÍDO! BANCO POPULADO.")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())