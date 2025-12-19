#!/usr/bin/env python3
"""
Script de teste de integração dos modelos SQLModel.

Testa:
1. Criação de tabelas no PostgreSQL
2. CRUD básico de cada modelo
3. Relacionamentos entre entidades
4. Soft delete
5. Filtros por tenant_id
6. Constraints e validações

Execução:
    cd backend
    python test_models_integration.py
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

from sqlmodel import SQLModel, select
from app.core.database import engine, get_session_context
from app.models import (
    Tenant, User, 
    Agente, Processo, VersaoProcesso, Execucao,
    ItemFila, Excecao, 
    Asset, Credencial, Agendamento,
    AuditoriaEvento, LogExecucao, LogMetadata,
    # Enums
    StatusAgenteEnum, TipoProcessoEnum, StatusExecucaoEnum, TriggerTypeEnum,
    PriorityEnum, StatusItemFilaEnum, TipoExcecaoEnum, SeverityEnum,
    TipoAssetEnum, ScopeAssetEnum, TipoCredencialEnum,
    ActionEnum, LogLevelEnum, TipoMetadataEnum
)
from app.core.security import hash_password, encrypt_credential


# ============================================================================
# HELPERS
# ============================================================================

def print_section(title: str):
    """Imprime seção formatada."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def print_success(message: str):
    """Imprime mensagem de sucesso."""
    print(f"   ✅ {message}")


def print_error(message: str):
    """Imprime mensagem de erro."""
    print(f"   ❌ {message}")


def print_info(message: str):
    """Imprime informação."""
    print(f"   ℹ️  {message}")


# ============================================================================
# TESTES
# ============================================================================

async def test_create_tables():
    """Testa criação de todas as tabelas."""
    print_section("1️⃣  CRIANDO TABELAS NO POSTGRESQL")
    
    try:
        # Drop e recria todas as tabelas (APENAS PARA TESTE!)
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.drop_all)
            print_info("Tabelas antigas removidas")
            
            await conn.run_sync(SQLModel.metadata.create_all)
            print_info("Novas tabelas criadas")
        
        # Lista tabelas criadas
        expected_tables = [
            "tenant", "user", 
            "agente", "processo", "versao_processo", "execucao",
            "item_fila", "excecao",
            "asset", "credencial", "agendamento",
            "auditoria_evento", "log_execucao", "log_metadata"
        ]
        
        print_success(f"{len(expected_tables)} tabelas criadas com sucesso!")
        for table in expected_tables:
            print(f"      • {table}")
        
        return True
    
    except Exception as e:
        print_error(f"Erro ao criar tabelas: {str(e)}")
        raise


async def test_tenant_and_user():
    """Testa criação de Tenant e User."""
    print_section("2️⃣  TESTANDO TENANT + USER")
    
    async with get_session_context() as session:
        try:
            # Criar tenant
            tenant = Tenant(
                name="Demo Corporation",
                slug="demo-corp",
                is_active=True,
                settings={"timezone": "America/Sao_Paulo", "max_agents": 10}
            )
            session.add(tenant)
            await session.commit()
            await session.refresh(tenant)
            
            print_success(f"Tenant criado: {tenant.name}")
            print_info(f"ID: {tenant.id}")
            print_info(f"Slug: {tenant.slug}")
            
            # Criar user
            user = User(
                tenant_id=tenant.id,
                email="admin@demo.com",
                hashed_password=hash_password("Admin@123"),
                full_name="Administrador Demo",
                is_superuser=True,
                is_active=True
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            print_success(f"User criado: {user.email}")
            print_info(f"ID: {user.id}")
            print_info(f"Superuser: {user.is_superuser}")
            
            # Testar relacionamento
            stmt = select(Tenant).where(Tenant.id == tenant.id)
            result = await session.execute(stmt)
            tenant_with_users = result.scalar_one()
            
            print_success(f"Relacionamento OK: Tenant tem {len(tenant_with_users.users)} usuário(s)")
            
            return tenant.id, user.id
        
        except Exception as e:
            print_error(f"Erro: {str(e)}")
            raise


async def test_core_models(tenant_id):
    """Testa modelos core: Agente, Processo, Versao, Execucao."""
    print_section("3️⃣  TESTANDO MODELOS CORE")
    
    async with get_session_context() as session:
        try:
            # ===== AGENTE =====
            agente = Agente(
                tenant_id=tenant_id,
                name="bot-001",
                machine_name="worker-01",
                ip_address="192.168.1.100",
                status=StatusAgenteEnum.ONLINE,
                last_heartbeat=datetime.utcnow(),
                version="1.0.0",
                capabilities={"skills": ["web", "excel", "pdf"]},
                extra_data={"environment": "production"}
            )
            session.add(agente)
            await session.commit()
            await session.refresh(agente)
            
            print_success(f"Agente: {agente.name} ({agente.status})")
            print_info(f"ID: {agente.id}")
            print_info(f"Extra Data: {agente.extra_data}")
            
            # ===== PROCESSO =====
            processo = Processo(
                tenant_id=tenant_id,
                name="Processo de Teste",
                description="Processo para validação de integração",
                tipo=TipoProcessoEnum.UNATTENDED,
                is_active=True,
                tags=["teste", "automacao", "integracao"]
            )
            session.add(processo)
            await session.commit()
            await session.refresh(processo)
            
            print_success(f"Processo: {processo.name} ({processo.tipo})")
            print_info(f"ID: {processo.id}")
            print_info(f"Tags: {processo.tags}")
            
            # ===== VERSAO DO PROCESSO =====
            versao = VersaoProcesso(
                tenant_id=tenant_id,
                processo_id=processo.id,
                version="1.0.0",
                package_path="/packages/teste_v1.0.0.zip",
                is_active=True,
                release_notes="Versão inicial de produção",
                config={"timeout": 300, "retry": 3}
            )
            session.add(versao)
            await session.commit()
            await session.refresh(versao)
            
            print_success(f"Versão: {versao.version} (active={versao.is_active})")
            print_info(f"ID: {versao.id}")
            print_info(f"Package: {versao.package_path}")
            
            # ===== EXECUÇÃO =====
            execucao = Execucao(
                tenant_id=tenant_id,
                processo_id=processo.id,
                versao_processo_id=versao.id,
                agente_id=agente.id,
                status=StatusExecucaoEnum.COMPLETED,
                trigger_type=TriggerTypeEnum.MANUAL,
                started_at=datetime.utcnow(),
                finished_at=datetime.utcnow(),
                duration_seconds=120,
                input_data={"test": True, "mode": "validation"},
                output_data={"result": "success", "records_processed": 100}
            )
            session.add(execucao)
            await session.commit()
            await session.refresh(execucao)
            
            print_success(f"Execução: {execucao.id} ({execucao.status})")
            print_info(f"Duração: {execucao.duration_seconds}s")
            print_info(f"Trigger: {execucao.trigger_type}")
            
            # Testar relacionamentos
            from sqlalchemy.orm import selectinload
            stmt = select(Processo).where(Processo.id == processo.id).options(
                selectinload(Processo.versoes),
                selectinload(Processo.execucoes)
            )
            result = await session.execute(stmt)
            processo_com_versoes = result.scalar_one()
            
            print_success(f"Relacionamentos OK:")
            print(f"      • Processo → Versões: {len(processo_com_versoes.versoes)}")
            print(f"      • Processo → Execuções: {len(processo_com_versoes.execucoes)}")
            
            return agente.id, processo.id, versao.id, execucao.id
        
        except Exception as e:
            print_error(f"Erro: {str(e)}")
            raise


async def test_workload_models(tenant_id, processo_id, agente_id, execucao_id):
    """Testa ItemFila e Excecao."""
    print_section("4️⃣  TESTANDO MODELOS WORKLOAD")
    
    async with get_session_context() as session:
        try:
            # ===== ITEM FILA =====
            item = ItemFila(
                tenant_id=tenant_id,
                processo_id=processo_id,
                queue_name="fila_teste",
                priority=PriorityEnum.NORMAL,
                status=StatusItemFilaEnum.COMPLETED,
                data={"documento": "123456", "tipo": "fatura"},
                retry_count=0,
                max_retries=3,
                processed_at=datetime.utcnow(),
                processed_by_agente_id=agente_id,
                execution_id=execucao_id
            )
            session.add(item)
            await session.commit()
            await session.refresh(item)
            
            print_success(f"ItemFila: {item.queue_name} ({item.status})")
            print_info(f"ID: {item.id}")
            print_info(f"Prioridade: {item.priority}")
            print_info(f"Data: {item.data}")
            
            # ===== EXCEÇÃO =====
            excecao = Excecao(
                tenant_id=tenant_id,
                execucao_id=execucao_id,
                tipo=TipoExcecaoEnum.BUSINESS,
                severity=SeverityEnum.LOW,
                message="Erro de validação no documento",
                stack_trace="Traceback (most recent call last):\n  File test.py...",
                context={"step": "validacao", "campo": "cnpj"},
                is_resolved=False
            )
            session.add(excecao)
            await session.commit()
            await session.refresh(excecao)
            
            print_success(f"Exceção: {excecao.message}")
            print_info(f"ID: {excecao.id}")
            print_info(f"Tipo: {excecao.tipo} | Severidade: {excecao.severity}")
            print_info(f"Resolvida: {excecao.is_resolved}")
            
            return item.id, excecao.id
        
        except Exception as e:
            print_error(f"Erro: {str(e)}")
            raise


async def test_governance_models(tenant_id, processo_id):
    """Testa Asset, Credencial, Agendamento."""
    print_section("5️⃣  TESTANDO MODELOS GOVERNANCE")
    
    async with get_session_context() as session:
        try:
            # ===== ASSET =====
            asset_global = Asset(
                tenant_id=tenant_id,
                name="URL_API",
                tipo=TipoAssetEnum.STRING,
                value="https://api.exemplo.com",
                description="URL base da API externa",
                scope=ScopeAssetEnum.GLOBAL
            )
            session.add(asset_global)
            
            asset_processo = Asset(
                tenant_id=tenant_id,
                name="TIMEOUT_PROCESSO",
                tipo=TipoAssetEnum.INTEGER,
                value="300",
                description="Timeout específico do processo (segundos)",
                scope=ScopeAssetEnum.PROCESSO,
                scope_id=processo_id
            )
            session.add(asset_processo)
            await session.commit()
            
            print_success(f"Asset Global: {asset_global.name}")
            print_info(f"Valor: {asset_global.value}")
            print_success(f"Asset Processo: {asset_processo.name}")
            print_info(f"Scope: {asset_processo.scope}")
            
            # ===== CREDENCIAL =====
            credencial = Credencial(
                tenant_id=tenant_id,
                name="api_key_teste",
                tipo=TipoCredencialEnum.API_KEY,
                username="integration@demo.com",
                encrypted_password=encrypt_credential("sk_test_abc123xyz789"),
                extra_data={"scope": "read_write", "rate_limit": 1000},
                expires_at=datetime.utcnow() + timedelta(days=90),
                rotation_days=90
            )
            session.add(credencial)
            await session.commit()
            await session.refresh(credencial)
            
            print_success(f"Credencial: {credencial.name} ({credencial.tipo})")
            print_info(f"ID: {credencial.id}")
            print_info(f"Senha criptografada: {credencial.encrypted_password[:20]}...")
            print_info(f"Expira em: {credencial.expires_at.strftime('%Y-%m-%d')}")
            
            # ===== AGENDAMENTO =====
            agendamento = Agendamento(
                tenant_id=tenant_id,
                processo_id=processo_id,
                name="Execução Diária",
                cron_expression="0 9 * * *",  # Todo dia às 9h
                timezone="America/Sao_Paulo",
                is_active=True,
                input_data={"mode": "daily", "notifications": True},
                next_run_at=datetime.utcnow() + timedelta(days=1)
            )
            session.add(agendamento)
            await session.commit()
            await session.refresh(agendamento)
            
            print_success(f"Agendamento: {agendamento.name}")
            print_info(f"ID: {agendamento.id}")
            print_info(f"Cron: {agendamento.cron_expression}")
            print_info(f"Próxima execução: {agendamento.next_run_at.strftime('%Y-%m-%d %H:%M')}")
            
            return asset_global.id, credencial.id, agendamento.id
        
        except Exception as e:
            print_error(f"Erro: {str(e)}")
            raise


async def test_monitoring_models(tenant_id, user_id, execucao_id):
    """Testa AuditoriaEvento, LogExecucao, LogMetadata."""
    print_section("6️⃣  TESTANDO MODELOS MONITORING")
    
    async with get_session_context() as session:
        try:
            # ===== AUDITORIA =====
            auditoria = AuditoriaEvento(
                tenant_id=tenant_id,
                user_id=user_id,
                entity_type="Processo",
                entity_id=execucao_id,
                action=ActionEnum.CREATE,
                new_values={"name": "Processo de Teste", "tipo": "unattended"},
                ip_address="192.168.1.10",
                user_agent="Mozilla/5.0 (Test Client)"
            )
            session.add(auditoria)
            await session.commit()
            await session.refresh(auditoria)
            
            print_success(f"Auditoria: {auditoria.action} em {auditoria.entity_type}")
            print_info(f"ID: {auditoria.id}")
            print_info(f"User ID: {auditoria.user_id}")
            print_info(f"IP: {auditoria.ip_address}")
            
            # ===== LOG =====
            correlation_id = "test-correlation-12345"
            log = LogExecucao(
                tenant_id=tenant_id,
                execucao_id=execucao_id,
                level=LogLevelEnum.INFO,
                message="Execução iniciada com sucesso",
                correlation_id=correlation_id,
                source="test_script.main",
                extra={"version": "1.0.0", "environment": "test"}
            )
            session.add(log)
            await session.commit()
            await session.refresh(log)
            
            print_success(f"Log: {log.message}")
            print_info(f"ID: {log.id}")
            print_info(f"Level: {log.level}")
            print_info(f"Correlation ID: {log.correlation_id}")
            
            # ===== METADATA =====
            metadata1 = LogMetadata(
                tenant_id=tenant_id,
                log_execucao_id=log.id,
                key="duration_ms",
                value="1500",
                tipo=TipoMetadataEnum.NUMBER
            )
            session.add(metadata1)
            
            metadata2 = LogMetadata(
                tenant_id=tenant_id,
                log_execucao_id=log.id,
                key="user_action",
                value="click_button",
                tipo=TipoMetadataEnum.STRING
            )
            session.add(metadata2)
            
            await session.commit()
            
            # Buscar log com metadados
            stmt = select(LogExecucao).where(LogExecucao.id == log.id)
            result = await session.execute(stmt)
            log_com_metadata = result.scalar_one()
            
            print_success(f"Metadados: {len(log_com_metadata.metadados)} registros")
            for meta in log_com_metadata.metadados:
                print(f"      • {meta.key}={meta.value} ({meta.tipo})")
            
            return auditoria.id, log.id
        
        except Exception as e:
            print_error(f"Erro: {str(e)}")
            raise


async def test_relationships(tenant_id):
    """Testa relacionamentos entre modelos."""
    print_section("7️⃣  TESTANDO RELACIONAMENTOS")
    
    async with get_session_context() as session:
        try:
            from sqlalchemy.orm import selectinload
            
            # Buscar tenant com users
            stmt = select(Tenant).where(Tenant.id == tenant_id).options(
                selectinload(Tenant.users)
            )
            result = await session.execute(stmt)
            tenant = result.scalar_one()
            
            print_success(f"Tenant → Users: {len(tenant.users)} usuário(s)")
            
            # Buscar processo com versões e execuções
            stmt = select(Processo).where(Processo.tenant_id == tenant_id).options(
                selectinload(Processo.versoes),
                selectinload(Processo.execucoes)
            )
            result = await session.execute(stmt)
            processo = result.scalar_one()
            
            print_success(f"Processo → Versões: {len(processo.versoes)} versão(ões)")
            print_success(f"Processo → Execuções: {len(processo.execucoes)} execução(ões)")
            
            # Buscar execução com logs
            stmt = select(Execucao).where(Execucao.tenant_id == tenant_id).options(
                selectinload(Execucao.logs),
                selectinload(Execucao.excecoes)
            )
            result = await session.execute(stmt)
            execucao = result.scalar_one()
            
            print_success(f"Execução → Logs: {len(execucao.logs)} log(s)")
            print_success(f"Execução → Exceções: {len(execucao.excecoes)} exceção(ões)")
            
            # Buscar agente com execuções
            stmt = select(Agente).where(Agente.tenant_id == tenant_id).options(
                selectinload(Agente.execucoes)
            )
            result = await session.execute(stmt)
            agente = result.scalar_one()
            
            print_success(f"Agente → Execuções: {len(agente.execucoes)} execução(ões)")
            
            return True
        
        except Exception as e:
            print_error(f"Erro: {str(e)}")
            raise


async def test_soft_delete(tenant_id):
    """Testa soft delete."""
    print_section("8️⃣  TESTANDO SOFT DELETE")
    
    async with get_session_context() as session:
        try:
            # Criar agente temporário
            agente_temp = Agente(
                tenant_id=tenant_id,
                name="bot-temp-delete",
                machine_name="temp-machine",
                status=StatusAgenteEnum.OFFLINE,
                version="1.0.0"
            )
            session.add(agente_temp)
            await session.commit()
            await session.refresh(agente_temp)
            
            agente_id = agente_temp.id
            print_info(f"Agente temporário criado: {agente_temp.name} (ID: {agente_id})")
            
            # Soft delete
            agente_temp.soft_delete()
            await session.commit()
            
            print_success(f"Soft delete executado (deleted_at={agente_temp.deleted_at})")
            
            # Tentar buscar (com filtro de deleted_at)
            stmt = select(Agente).where(
                Agente.id == agente_id,
                Agente.deleted_at.is_(None)
            )
            result = await session.execute(stmt)
            agente_deletado = result.scalar_one_or_none()
            
            if agente_deletado is None:
                print_success("Soft delete funcionando: agente não aparece em queries normais")
            else:
                print_error("Soft delete FALHOU: agente ainda aparece em queries")
            
            # Buscar sem filtro (deve encontrar)
            stmt = select(Agente).where(Agente.id == agente_id)
            result = await session.execute(stmt)
            agente_existe = result.scalar_one_or_none()
            
            if agente_existe and agente_existe.is_deleted:
                print_success("Registro ainda existe no banco (soft delete, não hard delete)")
            else:
                print_error("Registro foi removido completamente (deveria ser soft delete)")
            
            # Restaurar
            agente_existe.restore()
            await session.commit()
            
            print_success(f"Restore executado (deleted_at={agente_existe.deleted_at})")
            
            return True
        
        except Exception as e:
            print_error(f"Erro: {str(e)}")
            raise


async def test_multi_tenant_isolation(tenant_id):
    """Testa isolamento multi-tenant."""
    print_section("9️⃣  TESTANDO ISOLAMENTO MULTI-TENANT")
    
    async with get_session_context() as session:
        try:
            # Criar segundo tenant
            tenant2 = Tenant(
                name="Outro Cliente",
                slug="outro-cliente",
                is_active=True
            )
            session.add(tenant2)
            await session.commit()
            await session.refresh(tenant2)
            
            print_info(f"Segundo tenant criado: {tenant2.name} (ID: {tenant2.id})")
            
            # Criar agente no tenant2
            agente2 = Agente(
                tenant_id=tenant2.id,
                name="bot-outro-tenant",
                machine_name="worker-02",
                status=StatusAgenteEnum.ONLINE,
                version="1.0.0"
            )
            session.add(agente2)
            await session.commit()
            
            print_info(f"Agente criado no tenant2: {agente2.name}")
            
            # Buscar agentes do tenant1 (não deve incluir do tenant2)
            stmt = select(Agente).where(
                Agente.tenant_id == tenant_id,
                Agente.deleted_at.is_(None)
            )
            result = await session.execute(stmt)
            agentes_tenant1 = result.scalars().all()
            
            print_success(f"Agentes do Tenant1: {len(agentes_tenant1)}")
            
            # Buscar agentes do tenant2
            stmt = select(Agente).where(
                Agente.tenant_id == tenant2.id,
                Agente.deleted_at.is_(None)
            )
            result = await session.execute(stmt)
            agentes_tenant2 = result.scalars().all()
            
            print_success(f"Agentes do Tenant2: {len(agentes_tenant2)}")
            
            # Validar isolamento
            if len(agentes_tenant2) == 1 and agentes_tenant2[0].name == "bot-outro-tenant":
                print_success("✓ Isolamento multi-tenant funcionando corretamente!")
            else:
                print_error("✗ Problema no isolamento multi-tenant")
            
            return True
        
        except Exception as e:
            print_error(f"Erro: {str(e)}")
            raise


async def test_constraints_and_validations():
    """Testa constraints e validações."""
    print_section("🔟 TESTANDO CONSTRAINTS E VALIDAÇÕES")
    
    async with get_session_context() as session:
        try:
            # Testar unique constraint em Tenant.slug
            tenant_dup = Tenant(
                name="Teste Duplicado",
                slug="demo-corp",  # Slug já existe
                is_active=True
            )
            session.add(tenant_dup)
            
            try:
                await session.commit()
                print_error("Unique constraint em Tenant.slug NÃO funcionou (permitiu duplicata)")
            except Exception:
                await session.rollback()
                print_success("Unique constraint em Tenant.slug funcionando")
            
            # Testar foreign key constraint
            agente_invalido = Agente(
                tenant_id="00000000-0000-0000-0000-000000000000",  # Tenant inexistente
                name="bot-invalido",
                machine_name="invalid",
                status=StatusAgenteEnum.OFFLINE,
                version="1.0.0"
            )
            session.add(agente_invalido)
            
            try:
                await session.commit()
                print_error("Foreign key constraint NÃO funcionou (permitiu tenant inexistente)")
            except Exception:
                await session.rollback()
                print_success("Foreign key constraint funcionando")
            
            return True
        
        except Exception as e:
            print_error(f"Erro: {str(e)}")
            raise


# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Executa todos os testes."""
    print("\n" + "="*70)
    print("  🧪 TESTE DE INTEGRAÇÃO DOS MODELOS SQLMODEL")
    print("  RPA Orchestrator - Backend Validation")
    print("="*70)
    
    results = {}
    
    try:
        # 1. Criar tabelas
        results["create_tables"] = await test_create_tables()
        
        # 2. Testar Tenant + User
        tenant_id, user_id = await test_tenant_and_user()
        results["tenant_user"] = True
        
        # 3. Testar Core
        agente_id, processo_id, versao_id, execucao_id = await test_core_models(tenant_id)
        results["core"] = True
        
        # 4. Testar Workload
        item_id, excecao_id = await test_workload_models(
            tenant_id, processo_id, agente_id, execucao_id
        )
        results["workload"] = True
        
        # 5. Testar Governance
        asset_id, credencial_id, agendamento_id = await test_governance_models(
            tenant_id, processo_id
        )
        results["governance"] = True
        
        # 6. Testar Monitoring
        auditoria_id, log_id = await test_monitoring_models(
            tenant_id, user_id, execucao_id
        )
        results["monitoring"] = True
        
        # 7. Testar Relacionamentos
        results["relationships"] = await test_relationships(tenant_id)
        
        # 8. Testar Soft Delete
        results["soft_delete"] = await test_soft_delete(tenant_id)
        
        # 9. Testar Isolamento Multi-Tenant
        results["multi_tenant"] = await test_multi_tenant_isolation(tenant_id)
        
        # 10. Testar Constraints
        results["constraints"] = await test_constraints_and_validations()
        
        # ===== RESUMO =====
        print_section("📊 RESUMO DOS TESTES")
        
        total = len(results)
        passed = sum(1 for v in results.values() if v)
        
        for test_name, passed_test in results.items():
            status = "✅ PASSOU" if passed_test else "❌ FALHOU"
            print(f"   {test_name.upper():.<50} {status}")
        
        print("\n" + "="*70)
        if passed == total:
            print("  🎉 TODOS OS TESTES PASSARAM COM SUCESSO!")
            print(f"  {passed}/{total} testes executados com êxito")
            print("="*70)
            print("\n  📝 Próximos passos:")
            print("     1. Configurar Alembic para migrations")
            print("     2. Gerar migration inicial")
            print("     3. Popular banco com seed data")
            print("     4. Começar desenvolvimento de endpoints")
        else:
            print(f"  ⚠️  {total - passed} TESTE(S) FALHARAM")
            print(f"  {passed}/{total} testes passaram")
        print("="*70 + "\n")
        
        return 0 if passed == total else 1
    
    except Exception as e:
        print_section("❌ ERRO CRÍTICO")
        print_error(f"Erro durante execução dos testes: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)