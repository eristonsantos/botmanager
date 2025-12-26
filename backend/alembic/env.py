import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel
from alembic import context
from dotenv import load_dotenv

# 1. Configurar caminhos para importar a 'app'
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

# 2. Carregar variáveis de ambiente
env_file = backend_dir / ".env"
load_dotenv(env_file, override=True)

from app.core.config import settings

# 3. IMPORTAR TODOS OS MODELOS AQUI
# Isto é crucial para que o 'target_metadata' detecte as tabelas
from app.models.base import SQLModel
from app.models.tenant import Tenant, User
from app.models.core import Agente, Processo, VersaoProcesso, Execucao
from app.models.workload import ItemFila, Excecao
# Se tiveres mais modelos (ex: monitoring), importa-os aqui também

# 4. Configurar Metadados
target_metadata = SQLModel.metadata

# 5. Configuração de Logging do Alembic
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

def get_url():
    """Converte DATABASE_URL de asyncpg para psycopg2 para o Alembic."""
    url = settings.DATABASE_URL
    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql://")
    return url

def run_migrations_offline() -> None:
    """Executa migrações em modo 'offline'."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Executa migrações em modo 'online'."""
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            compare_type=True, # Detecta mudanças de tipo de coluna
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()