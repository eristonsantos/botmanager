# backend/app/core/database.py
"""
Configuração e gerenciamento de conexões com PostgreSQL usando SQLModel assíncrono.
Suporta connection pooling e dependency injection para FastAPI.
"""
from typing import AsyncGenerator
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    AsyncEngine,
    async_sessionmaker
)
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool
from sqlmodel import SQLModel

from app.core.config import settings
from app.core.logging import get_logger


logger = get_logger(__name__)


# ============================================================================
# ENGINE CONFIGURATION
# ============================================================================

def create_database_engine() -> AsyncEngine:
    """
    Cria e configura o engine assíncrono do SQLAlchemy.
    
    Configurações importantes:
    - Connection pooling para otimizar reutilização de conexões
    - Echo habilitado apenas em desenvolvimento
    - Pool recycle para evitar conexões stale
    
    Returns:
        AsyncEngine configurado
    """
    # Usar AsyncAdaptedQueuePool em todos os modos
    # NullPool causa problemas com greenlet em async context
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        future=True,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_timeout=settings.DATABASE_POOL_TIMEOUT,
        pool_recycle=settings.DATABASE_POOL_RECYCLE,
        poolclass=AsyncAdaptedQueuePool,
    )
    
    if settings.DEBUG:
        logger.info("Database engine created with AsyncAdaptedQueuePool (DEBUG mode)")
    else:
        logger.info(
            "Database engine created with AsyncAdaptedQueuePool",
            extra={
                "extra_data": {
                    "pool_size": settings.DATABASE_POOL_SIZE,
                    "max_overflow": settings.DATABASE_MAX_OVERFLOW,
                }
            }
        )
    
    return engine


# Engine global (singleton)
engine: AsyncEngine = create_database_engine()

# Session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ============================================================================
# SESSION MANAGEMENT
# ============================================================================

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency para injeção de sessão do banco de dados em endpoints FastAPI.
    
    Uso:
        @app.get("/example")
        async def example(session: AsyncSession = Depends(get_session)):
            ...
    
    Yields:
        AsyncSession configurada e pronta para uso
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {str(e)}")
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_session_context():
    """
    Context manager para uso direto de sessão (fora de endpoints FastAPI).
    
    Uso:
        async with get_session_context() as session:
            result = await session.execute(query)
    
    Yields:
        AsyncSession configurada
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {str(e)}")
            raise
        finally:
            await session.close()


# ============================================================================
# DATABASE INITIALIZATION
# ============================================================================

async def create_db_and_tables() -> None:
    """
    Cria todas as tabelas definidas nos modelos SQLModel.
    
    ⚠️ ATENÇÃO: Use apenas em desenvolvimento/testes!
    Em produção, use Alembic para migrations.
    """
    logger.info("Creating database tables...")
    
    async with engine.begin() as conn:
        # Importar todos os modelos aqui para garantir que estão registrados
        # TODO: Quando criar os modelos, importar aqui
        # from app.models import ...
        
        await conn.run_sync(SQLModel.metadata.create_all)
    
    logger.info("Database tables created successfully")


async def drop_db_and_tables() -> None:
    """
    Remove todas as tabelas do banco de dados.
    
    ⚠️ ATENÇÃO: Use apenas em desenvolvimento/testes!
    NUNCA use em produção!
    """
    if settings.is_production:
        raise RuntimeError("Cannot drop tables in production environment!")
    
    logger.warning("Dropping all database tables...")
    
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
    
    logger.warning("All database tables dropped")


# ============================================================================
# HEALTH CHECK
# ============================================================================

async def check_database_connection() -> bool:
    """
    Verifica se a conexão com o banco de dados está funcionando.
    
    Returns:
        True se conectado, False caso contrário
    """
    try:
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return False


async def get_database_latency() -> float:
    """
    Mede a latência da conexão com o banco de dados.
    
    Returns:
        Latência em milissegundos
    """
    import time
    from sqlalchemy import text
    
    try:
        start = time.time()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        latency = (time.time() - start) * 1000  # Converte para ms
        return round(latency, 2)
    except Exception as e:
        logger.error(f"Failed to measure database latency: {str(e)}")
        return -1.0


# ============================================================================
# LIFECYCLE MANAGEMENT
# ============================================================================

async def init_database() -> None:
    """
    Inicializa o banco de dados na startup da aplicação.
    Chamado no lifespan event do FastAPI.
    """
    logger.info("Initializing database connection...")
    
    # Verifica conexão
    is_connected = await check_database_connection()
    
    if not is_connected:
        logger.error("Failed to connect to database!")
        raise ConnectionError("Cannot connect to PostgreSQL database")
    
    logger.info("Database connection initialized successfully")


async def close_database() -> None:
    """
    Fecha conexões com o banco de dados no shutdown da aplicação.
    Chamado no lifespan event do FastAPI.
    """
    logger.info("Closing database connections...")
    
    await engine.dispose()
    
    logger.info("Database connections closed")