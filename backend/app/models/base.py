# backend/app/models/base.py
"""
Módulo base com classes abstratas e mixins para todos os modelos.

Define:
- BaseModel: Classe base com campos comuns (id, tenant_id, timestamps)
- SoftDeleteMixin: Mixin para soft delete
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, func
from sqlmodel import Field, SQLModel


class SoftDeleteMixin:
    """
    Mixin para implementar soft delete.

    Observação:
    - O campo deleted_at é definido no BaseModel.
    - Este mixin apenas oferece métodos utilitários.
    """

    def soft_delete(self) -> None:
        """Marca o registro como deletado (soft delete) em UTC (timezone-aware)."""
        self.deleted_at = datetime.now(timezone.utc)

    def restore(self) -> None:
        """Restaura um registro deletado."""
        self.deleted_at = None

    @property
    def is_deleted(self) -> bool:
        """Verifica se o registro está deletado."""
        return self.deleted_at is not None


class BaseModel(SQLModel, SoftDeleteMixin):
    """
    Classe base para todos os modelos do sistema.

    IMPORTANTE:
    - Não usar table=True aqui.
    - Os filhos usam table=True para criar sua própria tabela.
    """

    # Primary Key
    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        index=True,
        description="Identificador único do registro",
    )

    # Multi-tenancy obrigatório
    tenant_id: UUID = Field(
        foreign_key="tenant.id",
        index=True,
        nullable=False,
        description="ID do tenant (organização) proprietário do registro",
    )

    # Timestamps (timestamptz / timezone-aware)
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
        description="Data de criação do registro (UTC)",
    )

    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
            onupdate=func.now(),
        ),
        description="Data da última atualização do registro (UTC)",
    )

    deleted_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="Data de exclusão lógica (soft delete) (UTC)",
    )

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }
        from_attributes = True
