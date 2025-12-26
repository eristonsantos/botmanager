# backend/app/models/tenant.py
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from uuid import UUID, uuid4
from sqlalchemy import Column, String, DateTime
from sqlmodel import Field, Relationship, SQLModel, Index
from pydantic import EmailStr
from .base import BaseModel

if TYPE_CHECKING:
    from .core import Agente, Processo, Execucao
    from .monitoring import AuditoriaEvento

class Tenant(SQLModel, table=True):
    __tablename__ = "tenant"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    name: str = Field(max_length=100, unique=True, index=True)
    slug: str = Field(sa_column=Column(String(50), unique=True, index=True))
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relacionamentos
    users: List["User"] = Relationship(back_populates="tenant")

class User(BaseModel, table=True):
    __tablename__ = "user"
    
    # O id e o tenant_id já vêm do BaseModel via herança.
    # Não os redeclaramos aqui para evitar conflitos de mapeamento.
    
    email: EmailStr = Field(sa_column=Column(String(255), nullable=False, index=True))
    hashed_password: str = Field(max_length=255)
    full_name: str = Field(max_length=100)
    is_active: bool = Field(default=True, index=True)
    is_superuser: bool = Field(default=False)
    last_login: Optional[datetime] = Field(default=None)
    
    tenant: Tenant = Relationship(back_populates="users")
    auditorias: List["AuditoriaEvento"] = Relationship(back_populates="user")

# Index composto para garantir email único DENTRO de cada tenant
Index("idx_user_email_tenant", User.email, User.tenant_id, unique=True)