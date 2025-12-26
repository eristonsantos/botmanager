# backend/app/models/base.py
from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4
from sqlalchemy import text, DateTime
from sqlmodel import Field, SQLModel

class SoftDeleteMixin:
    def soft_delete(self) -> None:
        self.deleted_at = datetime.now(timezone.utc)

    def restore(self) -> None:
        self.deleted_at = None

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

class BaseModel(SQLModel, SoftDeleteMixin):
    """
    Classe base corrigida.
    O erro 'already assigned to Table' é evitado ao não instanciar 
    objetos sqlalchemy.Column diretamente no nível de classe da Base.
    """
    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        index=True,
        nullable=False
    )

    tenant_id: UUID = Field(
        foreign_key="tenant.id",
        index=True,
        nullable=False
    )

    # Usamos default_factory para o Python e server_default para o Banco
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={
            "server_default": text("CURRENT_TIMESTAMP"),
        }
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={
            "server_default": text("CURRENT_TIMESTAMP"),
            "onupdate": text("CURRENT_TIMESTAMP"),
        }
    )

    deleted_at: Optional[datetime] = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        nullable=True
    )