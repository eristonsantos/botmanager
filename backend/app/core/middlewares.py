# backend/app/core/middlewares.py
"""
Middlewares customizados para a aplicação.
Inclui correlation ID, logging de requests e outros.
"""
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.logging import (
    get_logger,
    set_correlation_id,
    generate_correlation_id,
    get_correlation_id
)
from app.core.config import settings


logger = get_logger(__name__)


# ============================================================================
# CORRELATION ID MIDDLEWARE
# ============================================================================

class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware que adiciona correlation_id a cada requisição.
    
    - Aceita X-Request-ID do cliente (se fornecido)
    - Gera novo UUID se não fornecido
    - Adiciona ao contexto para uso em logs
    - Retorna no response header
    """
    
    REQUEST_ID_HEADER = "X-Request-ID"
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Tenta extrair correlation_id do header
        correlation_id = request.headers.get(self.REQUEST_ID_HEADER)
        
        # Se não existir, gera novo
        if not correlation_id:
            correlation_id = generate_correlation_id()
        
        # Define no contexto para uso em toda a aplicação
        set_correlation_id(correlation_id)
        
        # Processa request
        try:
            response = await call_next(request)
        except Exception as e:
            # Garante que correlation_id está disponível mesmo em erros
            logger.exception(f"Unhandled exception in request: {str(e)}")
            raise
        
        # Adiciona correlation_id no response header
        response.headers[self.REQUEST_ID_HEADER] = correlation_id
        
        return response


# ============================================================================
# REQUEST LOGGING MIDDLEWARE
# ============================================================================

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware que loga informações de cada requisição.
    
    - Log de início da request
    - Log de fim com tempo de processamento
    - Informações sobre status code e path
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Registra início da request
        start_time = time.time()
        correlation_id = get_correlation_id()
        
        # Informações da request
        request_info = {
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params),
            "client_host": request.client.host if request.client else "unknown",
        }
        
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={"extra_data": request_info}
        )
        
        # Processa request
        try:
            response = await call_next(request)
        except Exception as e:
            # Loga erro
            duration = time.time() - start_time
            logger.error(
                f"Request failed: {request.method} {request.url.path}",
                extra={
                    "extra_data": {
                        **request_info,
                        "duration_ms": round(duration * 1000, 2),
                        "error": str(e),
                    }
                }
            )
            raise
        
        # Calcula duração
        duration = time.time() - start_time
        duration_ms = round(duration * 1000, 2)
        
        # Informações da response
        response_info = {
            **request_info,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        }
        
        # Log de conclusão
        log_level = "info"
        if response.status_code >= 500:
            log_level = "error"
        elif response.status_code >= 400:
            log_level = "warning"
        
        log_message = (
            f"Request completed: {request.method} {request.url.path} "
            f"- {response.status_code} - {duration_ms}ms"
        )
        
        getattr(logger, log_level)(
            log_message,
            extra={"extra_data": response_info}
        )
        
        # Adiciona header com tempo de processamento
        response.headers["X-Process-Time"] = str(duration_ms)
        
        return response


# ============================================================================
# TENANT VALIDATION MIDDLEWARE (FUTURO)
# ============================================================================

class TenantValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware para validação de tenant em requests autenticadas.
    
    ⚠️ Implementação futura quando tivermos modelo de Tenant no banco.
    Por enquanto, apenas valida presença do tenant_id no token.
    """
    
    # Rotas que não precisam de tenant validation
    EXEMPT_PATHS = [
        "/api/v1/health",
        "/api/v1/health/detailed",
        "/docs",
        "/redoc",
        "/openapi.json",
    ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Verifica se rota está na lista de exceções
        if any(request.url.path.startswith(path) for path in self.EXEMPT_PATHS):
            return await call_next(request)
        
        # TODO: Quando implementar autenticação obrigatória em rotas,
        # validar se tenant_id do token existe no banco
        
        response = await call_next(request)
        return response


# ============================================================================
# RATE LIMITING MIDDLEWARE (SIMPLIFICADO)
# ============================================================================

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware básico de rate limiting.
    
    ⚠️ Em produção, considere usar Redis para rate limiting distribuído.
    Esta implementação é in-memory e não funciona bem em múltiplas instâncias.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.requests: dict = {}  # {client_ip: [timestamps]}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)
        
        # Identifica cliente
        client_ip = request.client.host if request.client else "unknown"
        
        # Limpa requests antigos (mais de 1 minuto)
        current_time = time.time()
        if client_ip in self.requests:
            self.requests[client_ip] = [
                ts for ts in self.requests[client_ip]
                if current_time - ts < 60
            ]
        
        # Verifica limite
        request_count = len(self.requests.get(client_ip, []))
        
        if request_count >= settings.RATE_LIMIT_PER_MINUTE:
            from app.core.exceptions import RateLimitError
            
            logger.warning(
                f"Rate limit exceeded for {client_ip}",
                extra={"extra_data": {"client_ip": client_ip, "request_count": request_count}}
            )
            
            raise RateLimitError(
                details={
                    "limit": settings.RATE_LIMIT_PER_MINUTE,
                    "window": "1 minute",
                    "retry_after": 60
                }
            )
        
        # Registra request
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        self.requests[client_ip].append(current_time)
        
        response = await call_next(request)
        
        # Adiciona headers informativos
        response.headers["X-RateLimit-Limit"] = str(settings.RATE_LIMIT_PER_MINUTE)
        response.headers["X-RateLimit-Remaining"] = str(
            settings.RATE_LIMIT_PER_MINUTE - len(self.requests[client_ip])
        )
        
        return response