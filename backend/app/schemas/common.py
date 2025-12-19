# backend/app/schemas/common.py
"""
Schemas comuns reutilizáveis para toda a API.

Fornece:
- BaseSchema: Classe base Pydantic
- Mixins: TenantMixin, TimestampMixin
- PaginationParams e PaginatedResponse
- MessageResponse
"""

from datetime import datetime
from typing import TypeVar, Generic, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# ==================== BASE SCHEMA ====================

class BaseSchema(BaseModel):
    """Classe base para todos os schemas Pydantic"""
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }
    )


# ==================== MIXINS ====================

class TenantMixin(BaseModel):
    """Mixin para schemas com tenant_id"""
    
    tenant_id: UUID = Field(description="ID do tenant (organização)")


class TimestampMixin(BaseModel):
    """Mixin para schemas com timestamps"""
    
    created_at: datetime = Field(description="Data de criação")
    updated_at: datetime = Field(description="Data de última atualização")


# ==================== PAGINATION ====================

class PaginationParams(BaseSchema):
    """Parâmetros de paginação"""
    
    page: int = Field(
        default=1,
        ge=1,
        description="Página (começa em 1)"
    )
    
    size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Itens por página"
    )
    
    @property
    def skip(self) -> int:
        """Calcula offset para SQL"""
        return (self.page - 1) * self.size
    
    @property
    def limit(self) -> int:
        """Retorna limit para SQL"""
        return self.size


T = TypeVar("T")


class PaginatedResponse(BaseSchema, Generic[T]):
    """Response paginada genérica"""
    
    items: List[T] = Field(description="Lista de itens")
    total: int = Field(description="Total de itens (sem paginar)")
    page: int = Field(description="Página atual")
    size: int = Field(description="Itens por página")
    pages: int = Field(description="Total de páginas")
    
    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        params: PaginationParams
    ) -> "PaginatedResponse[T]":
        """
        Factory method para criar resposta paginada.
        
        Args:
            items: Lista de itens
            total: Total de registros
            params: Parâmetros de paginação
        
        Returns:
            PaginatedResponse com cálculos automáticos
        """
        import math
        
        pages = math.ceil(total / params.size) if total > 0 else 0
        
        return cls(
            items=items,
            total=total,
            page=params.page,
            size=params.size,
            pages=pages
        )


# ==================== GENERAL RESPONSES ====================

class MessageResponse(BaseSchema):
    """Response simples com mensagem"""
    
    message: str = Field(description="Mensagem")
    status: str = Field(
        default="success",
        description="Status (success, error, warning)"
    )


class ErrorResponse(BaseSchema):
    """Response de erro"""
    
    error: dict = Field(
        description="Detalhes do erro",
        example={
            "message": "Recurso não encontrado",
            "status_code": 404,
            "correlation_id": "abc-123"
        }
    )