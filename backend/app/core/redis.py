# backend/app/core/redis.py
"""
Configuração e gerenciamento de conexões com Redis.
Suporta cache, pub/sub e operações assíncronas.
"""
from typing import Optional, Any
import json
from contextlib import asynccontextmanager
import redis.asyncio as aioredis
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import settings
from app.core.logging import get_logger


logger = get_logger(__name__)


# ============================================================================
# REDIS CLIENT
# ============================================================================

class RedisClient:
    """
    Cliente Redis assíncrono com suporte a cache e operações básicas.
    Implementa singleton pattern para reutilização de conexões.
    """
    
    _instance: Optional["RedisClient"] = None
    _redis: Optional[Redis] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def connect(self) -> None:
        """Estabelece conexão com Redis."""
        if self._redis is not None:
            logger.warning("Redis already connected")
            return
        
        try:
            self._redis = await aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=settings.REDIS_DECODE_RESPONSES,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
            )
            
            # Testa conexão
            await self._redis.ping()
            
            logger.info(
                "Redis connection established",
                extra={
                    "extra_data": {
                        "url": settings.REDIS_URL.split("@")[-1],  # Remove credenciais do log
                        "max_connections": settings.REDIS_MAX_CONNECTIONS,
                    }
                }
            )
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            raise
    
    async def disconnect(self) -> None:
        """Fecha conexão com Redis."""
        if self._redis is not None:
            await self._redis.close()
            self._redis = None
            logger.info("Redis connection closed")
    
    @property
    def client(self) -> Redis:
        """Retorna o cliente Redis."""
        if self._redis is None:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return self._redis
    
    # ========================================================================
    # CACHE OPERATIONS
    # ========================================================================
    
    async def get_cache(self, key: str) -> Optional[Any]:
        """
        Busca valor do cache.
        
        Args:
            key: Chave do cache
        
        Returns:
            Valor deserializado ou None se não existir
        """
        try:
            value = await self.client.get(key)
            if value is None:
                return None
            
            # Tenta deserializar JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        except RedisError as e:
            logger.error(f"Redis GET error for key '{key}': {str(e)}")
            return None
    
    async def set_cache(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Define valor no cache.
        
        Args:
            key: Chave do cache
            value: Valor a ser armazenado (será serializado como JSON)
            ttl: Time to live em segundos (None = sem expiração)
        
        Returns:
            True se sucesso, False caso contrário
        """
        try:
            # Serializa valor como JSON
            if not isinstance(value, (str, bytes)):
                value = json.dumps(value, default=str)
            
            ttl = ttl or settings.CACHE_TTL_SECONDS
            
            await self.client.setex(key, ttl, value)
            return True
        except RedisError as e:
            logger.error(f"Redis SET error for key '{key}': {str(e)}")
            return False
    
    async def delete_cache(self, key: str) -> bool:
        """
        Remove valor do cache.
        
        Args:
            key: Chave do cache
        
        Returns:
            True se removido, False caso contrário
        """
        try:
            result = await self.client.delete(key)
            return result > 0
        except RedisError as e:
            logger.error(f"Redis DELETE error for key '{key}': {str(e)}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """
        Remove todas as chaves que correspondem ao padrão.
        
        Args:
            pattern: Padrão de chaves (ex: 'user:*')
        
        Returns:
            Número de chaves removidas
        """
        try:
            keys = []
            async for key in self.client.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                return await self.client.delete(*keys)
            return 0
        except RedisError as e:
            logger.error(f"Redis DELETE PATTERN error for pattern '{pattern}': {str(e)}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """
        Verifica se chave existe no cache.
        
        Args:
            key: Chave do cache
        
        Returns:
            True se existe, False caso contrário
        """
        try:
            result = await self.client.exists(key)
            return result > 0
        except RedisError as e:
            logger.error(f"Redis EXISTS error for key '{key}': {str(e)}")
            return False
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Incrementa valor numérico no cache.
        
        Args:
            key: Chave do cache
            amount: Valor a incrementar
        
        Returns:
            Novo valor ou None em caso de erro
        """
        try:
            return await self.client.incrby(key, amount)
        except RedisError as e:
            logger.error(f"Redis INCRBY error for key '{key}': {str(e)}")
            return None
    
    async def set_with_expire(self, key: str, value: Any, seconds: int) -> bool:
        """
        Define valor com expiração.
        Alias para set_cache com TTL.
        """
        return await self.set_cache(key, value, ttl=seconds)
    
    # ========================================================================
    # HEALTH CHECK
    # ========================================================================
    
    async def health_check(self) -> bool:
        """
        Verifica se Redis está respondendo.
        
        Returns:
            True se saudável, False caso contrário
        """
        try:
            await self.client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {str(e)}")
            return False
    
    async def get_latency(self) -> float:
        """
        Mede latência do Redis.
        
        Returns:
            Latência em milissegundos
        """
        import time
        
        try:
            start = time.time()
            await self.client.ping()
            latency = (time.time() - start) * 1000
            return round(latency, 2)
        except Exception as e:
            logger.error(f"Failed to measure Redis latency: {str(e)}")
            return -1.0


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

redis_client = RedisClient()


# ============================================================================
# DEPENDENCY FOR FASTAPI
# ============================================================================

async def get_redis() -> Redis:
    """
    Dependency para injeção do cliente Redis em endpoints FastAPI.
    
    Uso:
        @app.get("/example")
        async def example(redis: Redis = Depends(get_redis)):
            await redis.get("key")
    
    Returns:
        Cliente Redis conectado
    """
    return redis_client.client


# ============================================================================
# CONTEXT MANAGER
# ============================================================================

@asynccontextmanager
async def get_redis_context():
    """
    Context manager para uso direto do Redis (fora de endpoints).
    
    Uso:
        async with get_redis_context() as redis:
            await redis.get("key")
    """
    yield redis_client.client


# ============================================================================
# LIFECYCLE MANAGEMENT
# ============================================================================

async def init_redis() -> None:
    """
    Inicializa conexão com Redis na startup da aplicação.
    Chamado no lifespan event do FastAPI.
    """
    logger.info("Initializing Redis connection...")
    await redis_client.connect()
    logger.info("Redis connection initialized successfully")


async def close_redis() -> None:
    """
    Fecha conexão com Redis no shutdown da aplicação.
    Chamado no lifespan event do FastAPI.
    """
    logger.info("Closing Redis connection...")
    await redis_client.disconnect()
    logger.info("Redis connection closed")


# ============================================================================
# CACHE HELPERS
# ============================================================================

def make_cache_key(prefix: str, *args, tenant_id: Optional[str] = None) -> str:
    """
    Cria chave de cache padronizada.
    
    Args:
        prefix: Prefixo da chave (ex: 'user', 'process')
        *args: Argumentos para compor a chave
        tenant_id: ID do tenant (para multi-tenancy)
    
    Returns:
        Chave formatada (ex: 'tenant:abc:user:123')
    """
    parts = []
    
    if tenant_id:
        parts.extend(["tenant", tenant_id])
    
    parts.append(prefix)
    parts.extend(str(arg) for arg in args)
    
    return ":".join(parts)