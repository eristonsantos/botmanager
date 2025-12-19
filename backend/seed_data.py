#!/usr/bin/env python3
"""
Script de seed data para popular o banco com dados iniciais.

Cria:
- 2 Tenants (Demo Corp e Test Inc)
- 2 Users por tenant
- 2 Agentes por tenant
- 2 Processos por tenant (com versões)
- 1 Asset global e 1 por processo
- 1 Credencial por tenant
- 1 Agendamento por processo
- Alguns itens de fila e execuções de exemplo

Uso:
    python seed_data.py
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from uuid import uuid4

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlmodel import select

from app.core.database import get_session_context
from app.core.security.password import hash_password
from app.core.security.encryption import encrypt_credential
from app.models import (
    Tenant,
    User,
    Agente,
    Processo,
    VersaoProcesso,
    Execucao,
    ItemFila,
    Asset,
    Credencial,
    Agendamento,
    StatusAgenteEnum,
    TipoProcessoEnum,
    StatusExecucaoEnum,
    TriggerTypeEnum,
    StatusItemFilaEnum,
    PriorityEnum,
    TipoAssetEnum,
    ScopeAssetEnum,
    TipoCredencialEnum,
)


async def seed_tenants():
    """Cria tenants iniciais."""
    print("\n🏢 Criando Tenants...")
    
    async with get_session_context() as session:
        # Tenant 1: Demo Corp
        tenant1 = Tenant(
            id=uuid4(),
            name="Demo Corporation",
            slug="demo-corp",
            is_active=True,
            settings={
                "timezone": "America/Sao_Paulo",
                "language": "pt-BR",
                "max_concurrent_executions": 5,
            }
        )
        session.add(tenant1)
        
        # Tenant 2: Test Inc
        tenant2 = Tenant(
            id=uuid4(),
            name="Test Inc",
            slug="test-inc",
            is_active=True,
            settings={
                "timezone": "UTC",
                "language": "en-US",
                "max_concurrent_executions": 3,
            }
        )
        session.add(tenant2)
        
        await session.commit()
        await session.refresh(tenant1)
        await session.refresh(tenant2)
        
        print(f"   ✅ {tenant1.name} (ID: {tenant1.id})")
        print(f"   ✅ {tenant2.name} (ID: {tenant2.id})")
        
        return tenant1, tenant2


async def seed_users(tenant1: Tenant, tenant2: Tenant):
    """Cria usuários para cada tenant."""
    print("\n👤 Criando Usuários...")
    
    async with get_session_context() as session:
        users = []
        
        # Users Tenant 1
        admin1 = User(
            id=uuid4(),
            tenant_id=tenant1.id,
            email="admin@democorp.com",
            hashed_password=hash_password("Admin123!"),
            full_name="Admin Demo Corp",
            is_active=True,
            is_superuser=True,
        )
        users.append(admin1)
        
        user1 = User(
            id=uuid4(),
            tenant_id=tenant1.id,
            email="user@democorp.com",
            hashed_password=hash_password("User123!"),
            full_name="User Demo Corp",
            is_active=True,
            is_superuser=False,
        )
        users.append(user1)
        
        # Users Tenant 2
        admin2 = User(
            id=uuid4(),
            tenant_id=tenant2.id,
            email="admin@testinc.com",
            hashed_password=hash_password("Admin123!"),
            full_name="Admin Test Inc",
            is_active=True,
            is_superuser=True,
        )
        users.append(admin2)
        
        user2 = User(
            id=uuid4(),
            tenant_id=tenant2.id,
            email="user@testinc.com",
            hashed_password=hash_password("User123!"),
            full_name="User Test Inc",
            is_active=True,
            is_superuser=False,
        )
        users.append(user2)
        
        for user in users:
            session.add(user)
        
        await session.commit()
        
        for user in users:
            await session.refresh(user)
            print(f"   ✅ {user.email} ({'Admin' if user.is_superuser else 'User'})")
        
        return users


async def seed_agentes(tenant1: Tenant, tenant2: Tenant):
    """Cria agentes RPA para cada tenant."""
    print("\n🤖 Criando Agentes...")
    
    async with get_session_context() as session:
        agentes = []
        
        # Agentes Tenant 1
        bot1 = Agente(
            id=uuid4(),
            tenant_id=tenant1.id,
            name="BOT-PROD-01",
            machine_name="bot-server-01",
            ip_address="192.168.1.10",
            status=StatusAgenteEnum.ONLINE,
            last_heartbeat=datetime.utcnow(),
            capabilities=["web", "excel", "pdf"],
            version="1.0.0",
            extra_data={"environment": "production"},
        )
        agentes.append(bot1)
        
        bot2 = Agente(
            id=uuid4(),
            tenant_id=tenant1.id,
            name="BOT-DEV-01",
            machine_name="bot-server-02",
            ip_address="192.168.1.11",
            status=StatusAgenteEnum.OFFLINE,
            capabilities=["web", "sap"],
            version="1.0.0",
            extra_data={"environment": "development"},
        )
        agentes.append(bot2)
        
        # Agentes Tenant 2
        bot3 = Agente(
            id=uuid4(),
            tenant_id=tenant2.id,
            name="BOT-TEST-01",
            machine_name="test-bot-01",
            ip_address="192.168.2.10",
            status=StatusAgenteEnum.ONLINE,
            last_heartbeat=datetime.utcnow(),
            capabilities=["web", "excel"],
            version="1.0.0",
            extra_data={"environment": "test"},
        )
        agentes.append(bot3)
        
        for agente in agentes:
            session.add(agente)
        
        await session.commit()
        
        for agente in agentes:
            await session.refresh(agente)
            print(f"   ✅ {agente.name} ({agente.status.value})")
        
        return agentes


async def seed_processos(tenant1: Tenant, tenant2: Tenant, agentes: list):
    """Cria processos com versões."""
    print("\n⚙️  Criando Processos e Versões...")
    
    async with get_session_context() as session:
        processos = []
        
        # Processos Tenant 1
        proc1 = Processo(
            id=uuid4(),
            tenant_id=tenant1.id,
            name="Extração de Faturas",
            description="Extrai dados de faturas em PDF",
            tipo=TipoProcessoEnum.UNATTENDED,
            is_active=True,
            tags=["financeiro", "pdf"],
            extra_data={"sla_hours": 24},
        )
        session.add(proc1)
        await session.commit()
        await session.refresh(proc1)
        
        # Versão do processo 1
        versao1 = VersaoProcesso(
            id=uuid4(),
            tenant_id=tenant1.id,
            processo_id=proc1.id,
            version="1.0.0",
            package_path="/packages/extracao_faturas_v1.0.0.zip",
            is_active=True,
            release_notes="Versão inicial",
            config={"timeout": 300, "retry_count": 3},
        )
        session.add(versao1)
        processos.append((proc1, versao1))
        
        proc2 = Processo(
            id=uuid4(),
            tenant_id=tenant1.id,
            name="Validação de Cadastros",
            description="Valida cadastros no sistema SAP",
            tipo=TipoProcessoEnum.ATTENDED,
            is_active=True,
            tags=["sap", "validacao"],
            extra_data={"requires_approval": True},
        )
        session.add(proc2)
        await session.commit()
        await session.refresh(proc2)
        
        versao2 = VersaoProcesso(
            id=uuid4(),
            tenant_id=tenant1.id,
            processo_id=proc2.id,
            version="2.1.0",
            package_path="/packages/validacao_cadastros_v2.1.0.zip",
            is_active=True,
            release_notes="Melhorias de performance",
            config={"batch_size": 100},
        )
        session.add(versao2)
        processos.append((proc2, versao2))
        
        # Processos Tenant 2
        proc3 = Processo(
            id=uuid4(),
            tenant_id=tenant2.id,
            name="Teste Automatizado",
            description="Processo de teste",
            tipo=TipoProcessoEnum.UNATTENDED,
            is_active=True,
            tags=["test"],
            extra_data={},
        )
        session.add(proc3)
        await session.commit()
        await session.refresh(proc3)
        
        versao3 = VersaoProcesso(
            id=uuid4(),
            tenant_id=tenant2.id,
            processo_id=proc3.id,
            version="1.0.0",
            package_path="/packages/teste_v1.0.0.zip",
            is_active=True,
            release_notes="Primeira versão",
            config={},
        )
        session.add(versao3)
        processos.append((proc3, versao3))
        
        await session.commit()
        
        for proc, versao in processos:
            await session.refresh(proc)
            await session.refresh(versao)
            print(f"   ✅ {proc.name} (v{versao.version})")
        
        return processos


async def seed_assets_credenciais(tenant1: Tenant, tenant2: Tenant, processos: list):
    """Cria assets e credenciais."""
    print("\n🔐 Criando Assets e Credenciais...")
    
    async with get_session_context() as session:
        # Asset Global Tenant 1
        asset_global = Asset(
            id=uuid4(),
            tenant_id=tenant1.id,
            name="API_BASE_URL",
            tipo=TipoAssetEnum.STRING,
            value="https://api.example.com",
            description="URL base da API",
            scope=ScopeAssetEnum.GLOBAL,
        )
        session.add(asset_global)
        print("   ✅ Asset Global: API_BASE_URL")
        
        # Asset específico do processo
        proc1, _ = processos[0]
        asset_proc = Asset(
            id=uuid4(),
            tenant_id=tenant1.id,
            name="PDF_OUTPUT_PATH",
            tipo=TipoAssetEnum.STRING,
            value="/output/faturas/",
            description="Caminho de saída dos PDFs",
            scope=ScopeAssetEnum.PROCESSO,
            scope_id=proc1.id,
        )
        session.add(asset_proc)
        print(f"   ✅ Asset Processo: PDF_OUTPUT_PATH ({proc1.name})")
        
        # Credencial Tenant 1
        cred1 = Credencial(
            id=uuid4(),
            tenant_id=tenant1.id,
            name="SAP_CREDENTIALS",
            tipo=TipoCredencialEnum.BASIC_AUTH,
            username="sap_user",
            encrypted_password=encrypt_credential("SenhaSegura123!"),
            extra_data={"server": "sap.example.com", "client": "100"},
            expires_at=datetime.utcnow() + timedelta(days=90),
        )
        session.add(cred1)
        print("   ✅ Credencial: SAP_CREDENTIALS")
        
        await session.commit()


async def seed_agendamentos(processos: list):
    """Cria agendamentos cron."""
    print("\n📅 Criando Agendamentos...")
    
    async with get_session_context() as session:
        proc1, _ = processos[0]
        
        agendamento = Agendamento(
            id=uuid4(),
            tenant_id=proc1.tenant_id,
            processo_id=proc1.id,
            name="Extração Diária de Faturas",
            cron_expression="0 9 * * 1-5",  # 9h segunda a sexta
            timezone="America/Sao_Paulo",
            is_active=True,
            input_data={"source": "inbox", "priority": "high"},
            next_run_at=datetime.utcnow() + timedelta(hours=1),
        )
        session.add(agendamento)
        await session.commit()
        
        print(f"   ✅ {agendamento.name} ({agendamento.cron_expression})")


async def main():
    """Executa todos os seeds."""
    print("=" * 70)
    print("  🌱 SEED DATA - RPA ORCHESTRATOR")
    print("=" * 70)
    
    try:
        # 1. Tenants
        tenant1, tenant2 = await seed_tenants()
        
        # 2. Users
        users = await seed_users(tenant1, tenant2)
        
        # 3. Agentes
        agentes = await seed_agentes(tenant1, tenant2)
        
        # 4. Processos e Versões
        processos = await seed_processos(tenant1, tenant2, agentes)
        
        # 5. Assets e Credenciais
        await seed_assets_credenciais(tenant1, tenant2, processos)
        
        # 6. Agendamentos
        await seed_agendamentos(processos)
        
        print("\n" + "=" * 70)
        print("  ✅ SEED DATA CONCLUÍDO COM SUCESSO!")
        print("=" * 70)
        print("\n📝 Credenciais de Acesso:")
        print("   • admin@democorp.com / Admin123!")
        print("   • user@democorp.com / User123!")
        print("   • admin@testinc.com / Admin123!")
        print("=" * 70 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERRO: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())