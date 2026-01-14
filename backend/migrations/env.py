import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlmodel import SQLModel

from alembic import context

# ---------------------------------------------------------
# 1. Configurar Paths e Variáveis de Ambiente
# ---------------------------------------------------------
# Sobe um nível para achar a pasta 'app' (backend/)
backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

from dotenv import load_dotenv
# Carrega o .env da pasta backend
load_dotenv(backend_dir / ".env")

from app.core.config import settings

# ---------------------------------------------------------
# 2. Importar SEUS Models (Crucial para o Autogenerate)
# ---------------------------------------------------------
# Importe aqui TODOS os arquivos onde você define tabelas
from app.models.tenant import Tenant, User
from app.models.core import Agente, Processo, VersaoProcesso, Execucao
# from app.models.workload import ItemFila... (se tiver)

# Define onde o Alembic vai olhar para criar as tabelas
target_metadata = SQLModel.metadata

# ---------------------------------------------------------
# 3. Configuração Padrão do Alembic
# ---------------------------------------------------------
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# SOBRESCREVE a URL do .ini com a do .env
config.set_main_option("sqlalchemy.url", str(settings.DATABASE_URL))


def run_migrations_offline() -> None:
    """Roda migrações offline (gera SQL)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Roda migrações online (Async)."""
    
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())