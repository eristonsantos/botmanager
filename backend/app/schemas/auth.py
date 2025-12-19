"""
Schemas para autenticação e gestão de usuários.

Endpoints suportados:
- POST /auth/register
- POST /auth/login
- POST /auth/refresh
- GET  /auth/me
- PUT  /auth/me
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import EmailStr, Field, field_validator

from .common import BaseSchema, TimestampMixin, TenantMixin


# ==================== USER SCHEMAS ====================

class UserBase(BaseSchema):
    """Campos base do usuário (compartilhados)"""
    
    email: EmailStr = Field(
        description="Email único do usuário",
        examples=["admin@demo.com"]
    )
    
    full_name: str = Field(
        min_length=2,
        max_length=100,
        description="Nome completo do usuário",
        examples=["Admin User"]
    )


class UserCreate(UserBase):
    """Schema para criar novo usuário"""
    
    password: str = Field(
        min_length=8,
        max_length=100,
        description="Senha (será hasheada)",
        examples=["Admin123!"]
    )
    
    tenant_id: Optional[UUID] = Field(
        default=None,
        description="ID do tenant (opcional - pode ser auto-atribuído)"
    )
    
    is_superuser: bool = Field(
        default=False,
        description="Usuário com permissões de superuser"
    )
    
    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Valida força da senha"""
        if len(v) < 8:
            raise ValueError("Senha deve ter no mínimo 8 caracteres")
        
        # Verificar se tem pelo menos 1 número
        if not any(char.isdigit() for char in v):
            raise ValueError("Senha deve conter pelo menos 1 número")
        
        # Verificar se tem pelo menos 1 letra maiúscula
        if not any(char.isupper() for char in v):
            raise ValueError("Senha deve conter pelo menos 1 letra maiúscula")
        
        return v


class UserUpdate(BaseSchema):
    """Schema para atualizar usuário"""
    
    email: Optional[EmailStr] = Field(
        default=None,
        description="Novo email (opcional)"
    )
    
    full_name: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=100,
        description="Novo nome completo (opcional)"
    )
    
    password: Optional[str] = Field(
        default=None,
        min_length=8,
        max_length=100,
        description="Nova senha (opcional)"
    )
    
    is_active: Optional[bool] = Field(
        default=None,
        description="Ativar/desativar usuário"
    )
    
    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: Optional[str]) -> Optional[str]:
        """Valida força da senha (se fornecida)"""
        if v is None:
            return v
        
        if len(v) < 8:
            raise ValueError("Senha deve ter no mínimo 8 caracteres")
        
        if not any(char.isdigit() for char in v):
            raise ValueError("Senha deve conter pelo menos 1 número")
        
        if not any(char.isupper() for char in v):
            raise ValueError("Senha deve conter pelo menos 1 letra maiúscula")
        
        return v


class UserRead(UserBase, TenantMixin, TimestampMixin):
    """Schema para retornar usuário (response)"""
    
    id: UUID = Field(description="ID único do usuário")
    is_active: bool = Field(description="Usuário ativo no sistema")
    is_superuser: bool = Field(description="Possui permissões de superuser")
    last_login: Optional[datetime] = Field(
        default=None,
        description="Data do último login"
    )
    
    # IMPORTANTE: NUNCA retornar hashed_password
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "tenant_id": "123e4567-e89b-12d3-a456-426614174001",
                "email": "admin@demo.com",
                "full_name": "Admin User",
                "is_active": True,
                "is_superuser": True,
                "last_login": "2024-12-09T10:00:00Z",
                "created_at": "2024-12-01T10:00:00Z",
                "updated_at": "2024-12-09T10:00:00Z",
                "deleted_at": None
            }
        }
    }


# ==================== LOGIN SCHEMAS ====================

class LoginRequest(BaseSchema):
    """Schema para request de login"""
    
    email: EmailStr = Field(
        description="Email do usuário",
        examples=["admin@demo.com"]
    )
    
    password: str = Field(
        description="Senha do usuário",
        examples=["Admin123!"]
    )
    
    tenant_slug: Optional[str] = Field(
        default=None,
        description="Slug do tenant (opcional se usuário pertence a apenas 1 tenant)",
        examples=["demo-corp"]
    )


class TokenResponse(BaseSchema):
    """Schema para resposta com tokens JWT"""
    
    access_token: str = Field(description="Token de acesso (expira em 30 min)")
    refresh_token: str = Field(description="Token de renovação (expira em 7 dias)")
    token_type: str = Field(
        default="bearer",
        description="Tipo do token (sempre 'bearer')"
    )
    expires_in: int = Field(
        description="Tempo de expiração do access_token em segundos",
        examples=[1800]
    )
    user: UserRead = Field(description="Dados do usuário autenticado")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIs...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
                "token_type": "bearer",
                "expires_in": 1800,
                "user": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "email": "admin@demo.com",
                    "full_name": "Admin User",
                    "is_active": True
                }
            }
        }
    }


class RefreshTokenRequest(BaseSchema):
    """Schema para request de renovação de token"""
    
    refresh_token: str = Field(
        description="Refresh token válido",
        examples=["eyJhbGciOiJIUzI1NiIs..."]
    )


# ==================== TENANT SCHEMAS (BÁSICO) ====================

class TenantRead(BaseSchema, TimestampMixin):
    """Schema básico para retornar tenant"""
    
    id: UUID = Field(description="ID único do tenant")
    name: str = Field(description="Nome do tenant")
    slug: str = Field(description="Slug único (URL-friendly)")
    is_active: bool = Field(description="Tenant ativo")
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174001",
                "name": "Demo Corporation",
                "slug": "demo-corp",
                "is_active": True,
                "created_at": "2024-12-01T10:00:00Z",
                "updated_at": "2024-12-09T10:00:00Z",
                "deleted_at": None
            }
        }
    }
