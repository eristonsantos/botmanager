#backend/app/models/tenant.py
"""
Módulo de autenticação e multi-tenancy.

Define:
- Tenant: Organizações/clientes da plataforma
- User: Usuários do sistema vinculados a tenants
"""

from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel, Column, String, JSON, Index, DateTime
from sqlalchemy import func
from pydantic import EmailStr

# Importar BaseModel
from .base import BaseModel

if TYPE_CHECKING:
    from .core import Agente, Processo, Execucao
    from .monitoring import AuditoriaEvento


class Tenant(SQLModel, table=True):
    """
    Representa uma organização/cliente na plataforma (multi-tenant).
    
    Cada tenant é completamente isolado dos demais.
    Todos os recursos do sistema pertencem a um tenant.
    """
    
    __tablename__ = "tenant"
    
    # Primary Key
    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        index=True
    )
    
    # Identificação
    name: str = Field(
        max_length=100,
        unique=True,
        index=True,
        description="Nome da organização"
    )
    
    slug: str = Field(
        sa_column=Column(String(50), unique=True, index=True),
        description="Slug único para URLs (ex: acme-corp)"
    )
    
    # Status
    is_active: bool = Field(
        default=True,
        index=True,
        description="Tenant ativo na plataforma"
    )
    
    # Configurações customizadas por tenant
    settings: dict = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Configurações específicas do tenant (JSON)"
    )
    
    # Relacionamentos
    users: List["User"] = Relationship(
        back_populates="tenant",
        sa_relationship_kwargs={"lazy": "selectin", "cascade": "all, delete-orphan"}
    )
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }
        from_attributes = True
    
    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, name={self.name}, slug={self.slug})>"


class User(BaseModel, table=True):
    """
    Usuário do sistema vinculado a um tenant.
    
    Gerencia autenticação, autorização e auditoria de ações.
    
    Campos herdados de BaseModel:
    - id: UUID (primary key)
    - tenant_id: UUID (foreign key para tenant.id)
    - created_at: datetime
    - updated_at: datetime
    - deleted_at: datetime (soft delete)
    """
    
    __tablename__ = "user"
    
    # Autenticação
    email: EmailStr = Field(
        sa_column=Column(String(255), nullable=False, index=True),
        description="Email único por tenant"
    )
    
    hashed_password: str = Field(
        max_length=255,
        description="Senha hash (bcrypt/argon2)"
    )
    
    # Dados pessoais
    full_name: str = Field(
        max_length=100,
        description="Nome completo do usuário"
    )
    
    # Status e permissões
    is_active: bool = Field(
        default=True,
        index=True,
        description="Usuário ativo no sistema"
    )
    
    is_superuser: bool = Field(
        default=False,
        description="Superusuário com permissões totais no tenant"
    )
    
    # Controle de sessão
    last_login: Optional[datetime] = Field(
        default=None,
        description="Data do último login"
    )
    
    # Relacionamentos
    tenant: Tenant = Relationship(
        back_populates="users",
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    
    auditorias: List["AuditoriaEvento"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"lazy": "select"}
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, tenant_id={self.tenant_id})>"


# Indexes compostos para otimização
Index('idx_user_tenant_email', User.tenant_id, User.email, unique=True)
Index('idx_user_tenant_active', User.tenant_id, User.is_active)
Index('idx_user_deleted', User.deleted_at)