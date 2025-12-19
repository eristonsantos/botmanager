# backend/app/core/executions.py
"""
Exceções customizadas e handlers globais para a aplicação.
Padroniza respostas de erro com correlation_id e estrutura consistente.
"""
from typing import Any, Dict, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger, get_correlation_id


logger = get_logger(__name__)


# Base Exception
class AppException(Exception):
    """Exceção base para todas as exceções customizadas da aplicação."""
    
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


# Domain Exceptions
class DatabaseError(AppException):
    """Erro relacionado ao banco de dados."""
    
    def __init__(self, message: str = "Erro ao acessar banco de dados", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )


class NotFoundError(AppException):
    """Recurso não encontrado."""
    
    def __init__(self, resource: str, identifier: Any, details: Optional[Dict[str, Any]] = None):
        message = f"{resource} com identificador '{identifier}' não encontrado"
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details or {"resource": resource, "identifier": str(identifier)}
        )


class ValidationError(AppException):
    """Erro de validação de dados."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )


class AuthenticationError(AppException):
    """Erro de autenticação."""
    
    def __init__(self, message: str = "Não autenticado", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details
        )


class AuthorizationError(AppException):
    """Erro de autorização/permissão."""
    
    def __init__(self, message: str = "Acesso negado", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            details=details
        )


class ConflictError(AppException):
    """Conflito de recurso (ex: duplicação)."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            details=details
        )


class BusinessRuleError(AppException):
    """Violação de regra de negócio."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details
        )


class TenantError(AppException):
    """Erro relacionado a multi-tenancy."""
    
    def __init__(self, message: str = "Tenant inválido ou não especificado", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details
        )


class RateLimitError(AppException):
    """Taxa de requisições excedida."""
    
    def __init__(self, message: str = "Taxa de requisições excedida", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details
        )


# Exception Handlers
def create_error_response(
    status_code: int,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None
) -> JSONResponse:
    """Cria uma resposta de erro padronizada."""
    error_response = {
        "error": {
            "message": message,
            "status_code": status_code,
            "correlation_id": correlation_id or get_correlation_id() or "unknown",
        }
    }
    
    if details:
        error_response["error"]["details"] = details
    
    return JSONResponse(
        status_code=status_code,
        content=error_response
    )


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handler para exceções customizadas da aplicação."""
    correlation_id = get_correlation_id()
    
    logger.error(
        f"AppException: {exc.message}",
        extra={
            "extra_data": {
                "status_code": exc.status_code,
                "details": exc.details,
                "path": request.url.path,
                "method": request.method,
            }
        }
    )
    
    return create_error_response(
        status_code=exc.status_code,
        message=exc.message,
        details=exc.details,
        correlation_id=correlation_id
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handler para exceções HTTP padrão."""
    correlation_id = get_correlation_id()
    
    logger.warning(
        f"HTTPException: {exc.detail}",
        extra={
            "extra_data": {
                "status_code": exc.status_code,
                "path": request.url.path,
                "method": request.method,
            }
        }
    )
    
    return create_error_response(
        status_code=exc.status_code,
        message=str(exc.detail),
        correlation_id=correlation_id
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handler para erros de validação do Pydantic."""
    correlation_id = get_correlation_id()
    
    # Formata erros de validação de forma amigável
    errors = []
    for error in exc.errors():
        errors.append({
            "field": " -> ".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    logger.warning(
        "Validation error",
        extra={
            "extra_data": {
                "errors": errors,
                "path": request.url.path,
                "method": request.method,
            }
        }
    )
    
    return create_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        message="Erro de validação nos dados enviados",
        details={"validation_errors": errors},
        correlation_id=correlation_id
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handler genérico para exceções não tratadas."""
    correlation_id = get_correlation_id()
    
    logger.exception(
        f"Unhandled exception: {str(exc)}",
        extra={
            "extra_data": {
                "path": request.url.path,
                "method": request.method,
                "exception_type": type(exc).__name__,
            }
        }
    )
    
    # Em produção, não exponha detalhes internos
    from app.core.config import settings
    
    if settings.is_production:
        message = "Erro interno do servidor"
        details = None
    else:
        message = f"Erro interno: {str(exc)}"
        details = {"exception_type": type(exc).__name__}
    
    return create_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message=message,
        details=details,
        correlation_id=correlation_id
    )