"""
Configuração do ambiente Alembic para SQLModel.

Este arquivo é executado sempre que o Alembic roda migrations.
Configurado para:
- Carregar .env ANTES de importar settings
- Carregar modelos SQLModel automaticamente
- Usar DATABASE_URL do .env (convertendo asyncpg para psycopg2)
- Suportar migrations online e offline
"""
from logging.config import fileConfig
import sys
from pathlib import Path

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlmodel import SQLModel

from alembic import context

# ============================================================================
# ADICIONA O DIRETÓRIO backend/ AO PATH
# ============================================================================
# Permite importar app.models mesmo estando em alembic/
# Path(__file__) = .../backend/alembic/env.py
# .parent = .../backend/alembic/
# .parent.parent = .../backend/
backend_dir = Path(__file__).resolve().parent.parent  # .../backend/
sys.path.insert(0, str(backend_dir))

# ============================================================================
# CARREGA .env ANTES DE IMPORTAR SETTINGS
# ============================================================================
# CRÍTICO: O .env está em backend/, não na raiz!
# Pydantic-settings procura na raiz por padrão, então forçamos o path
from dotenv import load_dotenv
env_file = backend_dir / ".env"
load_dotenv(env_file, override=True)

# ============================================================================
# IMPORTA CONFIGURAÇÕES E MODELOS
# ============================================================================
from app.core.config import settings

# CRÍTICO: Importar TODOS os modelos para que sejam registrados no metadata
# Não precisa fazer nada com eles, apenas importar força o registro
from app.models import (
    Tenant,
    User,
    Agente,
    Processo,
    VersaoProcesso,
    Execucao,
    ItemFila,
    Excecao,
    Asset,
    Credencial,
    Agendamento,
    AuditoriaEvento,
    LogExecucao,
    LogMetadata,
)

# ============================================================================
# CONFIGURAÇÃO DO ALEMBIC
# ============================================================================
config = context.config

# Interpreta o arquivo de configuração para logging do Python
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# CRÍTICO: Converte DATABASE_URL de asyncpg (assíncrono) para psycopg2 (síncrono)
# Alembic precisa de driver síncrono
database_url = settings.DATABASE_URL
if "postgresql+asyncpg" in database_url:
    database_url = database_url.replace("postgresql+asyncpg", "postgresql+psycopg2")

config.set_main_option("sqlalchemy.url", database_url)

# CRÍTICO: Usar SQLModel.metadata que contém TODAS as tabelas
# (incluindo Tenant que herda de SQLModel e User/outros que herdam de BaseModel)
target_metadata = SQLModel.metadata

# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    Este modo gera SQL scripts ao invés de executar diretamente no banco.
    Útil para revisar mudanças antes de aplicar ou para bancos em produção.

    Uso:
        alembic upgrade head --sql > migration.sql
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Opções para comparação de tipos
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    Este modo conecta ao banco e executa as migrations diretamente.
    Modo padrão para desenvolvimento e staging.

    Neste cenário, o Engine é criado e associado ao contexto.
    """
    # Configuração do engine
    configuration = config.get_section(config.config_ini_section)
    
    # IMPORTANTE: Usa a URL já convertida para psycopg2
    configuration["sqlalchemy.url"] = config.get_main_option("sqlalchemy.url")
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # Não usar pool em migrations
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Opções para comparação
            compare_type=True,
            compare_server_default=True,
            # Incluir schemas (para multi-schema no futuro)
            include_schemas=False,
            # Renderizar batch alterations para SQLite (se necessário)
            render_as_batch=False,
        )

        with context.begin_transaction():
            context.run_migrations()


# ============================================================================
# EXECUÇÃO
# ============================================================================
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()