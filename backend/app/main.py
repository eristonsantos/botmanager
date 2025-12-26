# backend/app/main.py

"""
Aplicação principal FastAPI - RPA Orchestrator.

Orquestrador de automações RPA multi-tenant com suporte a:
- Gestão de agentes (robôs)
- Processos e versões
- Execuções e filas
- Credenciais e assets
- Monitoramento e auditoria
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.core.database import init_database, close_database
from app.core.redis import init_redis, close_redis
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)
from app.core.middlewares import (
    CorrelationIDMiddleware,
    RequestLoggingMiddleware,
    RateLimitMiddleware,
)

# ATUALIZADO: Importando os novos routers explicitamente
from app.api.v1 import (
    api_router,     # Routers antigos (Health, Auth, Agents) agregados no __init__
    processes,      # Fase 5A
    executions,     # Fase 5B
    governance      # Assets & Credenciais
)


# Configurar logging antes de tudo
setup_logging()
logger = get_logger(__name__)


# ============================================================================
# LIFESPAN EVENTS
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Gerencia eventos de startup e shutdown da aplicação.
    """
    # ========================================================================
    # STARTUP
    # ========================================================================
    logger.info(
        f"Starting {settings.APP_NAME}...",
        extra={
            "extra_data": {
                "version": settings.API_VERSION,
                "environment": settings.ENVIRONMENT,
                "debug": settings.DEBUG,
            }
        }
    )
    
    try:
        # Inicializa banco de dados
        await init_database()
        
        # Inicializa Redis
        await init_redis()
        
        # Em DEV, pode-se descomentar para criar tabelas, mas recomendamos Alembic
        # if settings.is_development:
        #     from app.core.database import create_db_and_tables
        #     await create_db_and_tables()
        
        logger.info(
            f"{settings.APP_NAME} started successfully!",
            extra={
                "extra_data": {
                    "host": settings.HOST,
                    "port": settings.PORT,
                    "docs_url": f"http://{settings.HOST}:{settings.PORT}/docs",
                }
            }
        )
    
    except Exception as e:
        logger.exception(f"Failed to start application: {str(e)}")
        raise
    
    # Aplicação rodando
    yield
    
    # ========================================================================
    # SHUTDOWN
    # ========================================================================
    logger.info(f"Shutting down {settings.APP_NAME}...")
    
    try:
        # Fecha conexões
        await close_database()
        await close_redis()
        
        logger.info(f"{settings.APP_NAME} shut down successfully")
    
    except Exception as e:
        logger.exception(f"Error during shutdown: {str(e)}")


# ============================================================================
# FASTAPI APP INITIALIZATION
# ============================================================================

def create_application() -> FastAPI:
    """
    Factory para criar e configurar a aplicação FastAPI.
    """
    # Cria aplicação
    app = FastAPI(
        title=settings.APP_NAME,
        description=settings.APP_DESCRIPTION,
        version=settings.API_VERSION,
        debug=settings.DEBUG,
        lifespan=lifespan,
        # Customiza documentação
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        contact={
            "name": "RPA Orchestrator Team",
            "email": "support@rpaorchestrator.com",
        },
        license_info={
            "name": "Proprietary",
        },
    )
    
    # ========================================================================
    # CORS MIDDLEWARE
    # ========================================================================
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )
    
    # ========================================================================
    # CUSTOM MIDDLEWARES
    # ========================================================================
    
    # Rate limiting
    if settings.RATE_LIMIT_ENABLED:
        app.add_middleware(RateLimitMiddleware)
    
    # Request logging
    app.add_middleware(RequestLoggingMiddleware)
    
    # Correlation ID
    app.add_middleware(CorrelationIDMiddleware)
    
    # ========================================================================
    # EXCEPTION HANDLERS
    # ========================================================================
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
    
    # ========================================================================
    # ROUTERS
    # ========================================================================
    
    # 1. Routers Base (Auth, Agents, Health)
    # Assumindo que api_router agrega estes no __init__.py de v1
    app.include_router(
        api_router,
        prefix=settings.api_prefix
    )
    
    # 2. Novos Routers - Fase 5A: Processos
    app.include_router(
        processes.router,
        prefix=f"{settings.api_prefix}/processes",
        tags=["Processos"]
    )

    # 3. Novos Routers - Fase 5B: Execuções
    app.include_router(
        executions.router,
        prefix=f"{settings.api_prefix}/executions",
        tags=["Execuções"]
    )

    # 4. Novos Routers - Governança: Assets & Credenciais
    app.include_router(
        governance.router,
        prefix=f"{settings.api_prefix}/governance",
        tags=["Governança"]
    )
    
    # ========================================================================
    # ROOT ENDPOINT
    # ========================================================================
    @app.get(
        "/",
        tags=["Root"],
        summary="Root Endpoint",
        description="Informações básicas da API"
    )
    async def root():
        """Endpoint raiz com informações da API."""
        return {
            "name": settings.APP_NAME,
            "version": settings.API_VERSION,
            "environment": settings.ENVIRONMENT,
            "docs": "/docs",
            "redoc": "/redoc",
            "health": f"{settings.api_prefix}/health",
        }
    
    return app


# ============================================================================
# APP INSTANCE & RUNNER
# ============================================================================

app = create_application()

if __name__ == "__main__":
    import uvicorn
    
    uvicorn_config = {
        "app": "app.main:app",
        "host": settings.HOST,
        "port": settings.PORT,
        "reload": settings.DEBUG,
        "log_level": settings.LOG_LEVEL.lower(),
        "access_log": True,
    }
    
    logger.info(
        "Starting Uvicorn server...",
        extra={"extra_data": uvicorn_config}
    )
    
    uvicorn.run(**uvicorn_config)