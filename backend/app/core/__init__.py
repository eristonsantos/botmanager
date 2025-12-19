# backend/app/core/__init__.py
"""
Core package - Módulos fundamentais da aplicação.
"""
from app.core.config import settings, get_settings
from app.core.logging import get_logger, get_correlation_id, set_correlation_id
from app.core.database import get_session, engine
from app.core.redis import redis_client, get_redis


__all__ = [
    "settings",
    "get_settings",
    "get_logger",
    "get_correlation_id",
    "set_correlation_id",
    "get_session",
    "engine",
    "redis_client",
    "get_redis",
]