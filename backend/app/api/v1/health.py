# backend/app/api/v1/health.py
"""
Endpoints de health check para monitoramento da aplicação.
"""
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, status

from app.core.config import settings
from app.core.database import check_database_connection, get_database_latency
from app.core.redis import redis_client
from app.core.logging import get_logger


logger = get_logger(__name__)

router = APIRouter(prefix="/health", tags=["Health Check"])


@router.get(
    "",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Health Check Básico",
    description="Verifica se a API está respondendo. Não verifica dependências externas."
)
async def health_check() -> Dict[str, Any]:
    """
    Health check básico da API.
    
    Retorna:
        - status: Estado da aplicação
        - timestamp: Timestamp atual em ISO 8601
        - version: Versão da API
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": settings.API_VERSION,
        "environment": settings.ENVIRONMENT,
    }


@router.get(
    "/detailed",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Health Check Detalhado",
    description="Verifica status de todas as dependências: PostgreSQL e Redis."
)
async def detailed_health_check() -> Dict[str, Any]:
    """
    Health check detalhado incluindo status de dependências.
    
    Verifica:
        - PostgreSQL (conexão e latência)
        - Redis (conexão e latência)
    
    Retorna:
        - status: Estado geral (healthy se todas dependências OK)
        - timestamp: Timestamp atual
        - version: Versão da API
        - services: Status detalhado de cada serviço
    """
    services = {}
    overall_status = "healthy"
    
    # PostgreSQL check
    try:
        db_connected = await check_database_connection()
        db_latency = await get_database_latency() if db_connected else -1
        
        services["database"] = {
            "name": "PostgreSQL",
            "status": "connected" if db_connected else "disconnected",
            "latency_ms": db_latency,
        }
        
        if not db_connected:
            overall_status = "degraded"
            logger.error("Database health check failed")
    
    except Exception as e:
        services["database"] = {
            "name": "PostgreSQL",
            "status": "error",
            "error": str(e),
        }
        overall_status = "unhealthy"
        logger.exception("Database health check exception")
    
    # Redis check
    try:
        redis_connected = await redis_client.health_check()
        redis_latency = await redis_client.get_latency() if redis_connected else -1
        
        services["redis"] = {
            "name": "Redis",
            "status": "connected" if redis_connected else "disconnected",
            "latency_ms": redis_latency,
        }
        
        if not redis_connected:
            overall_status = "degraded"
            logger.error("Redis health check failed")
    
    except Exception as e:
        services["redis"] = {
            "name": "Redis",
            "status": "error",
            "error": str(e),
        }
        overall_status = "unhealthy"
        logger.exception("Redis health check exception")
    
    response = {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": settings.API_VERSION,
        "environment": settings.ENVIRONMENT,
        "services": services,
    }
    
    if overall_status != "healthy":
        logger.warning(
            f"Health check status: {overall_status}",
            extra={"extra_data": {"services": services}}
        )
    
    return response


@router.get(
    "/ready",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Readiness Check",
    description="Verifica se a aplicação está pronta para receber tráfego (para Kubernetes)."
)
async def readiness_check() -> Dict[str, Any]:
    """
    Readiness probe para Kubernetes.
    
    Verifica se todas as dependências críticas estão funcionando.
    Retorna 200 se pronto, 503 se não estiver pronto.
    """
    try:
        db_ok = await check_database_connection()
        redis_ok = await redis_client.health_check()
        
        if db_ok and redis_ok:
            return {
                "status": "ready",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        else:
            return {
                "status": "not_ready",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "details": {
                    "database": "ok" if db_ok else "not_ready",
                    "redis": "ok" if redis_ok else "not_ready",
                }
            }
    
    except Exception as e:
        logger.exception("Readiness check failed")
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "error": str(e),
        }


@router.get(
    "/live",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Liveness Check",
    description="Verifica se a aplicação está viva (para Kubernetes)."
)
async def liveness_check() -> Dict[str, Any]:
    """
    Liveness probe para Kubernetes.
    
    Verifica apenas se a aplicação está rodando.
    Não verifica dependências externas.
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }