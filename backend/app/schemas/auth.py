# backend/app/schemas/auth.py
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import EmailStr, Field, field_validator, ConfigDict
from .common import BaseSchema, TimestampMixin, TenantMixin

# ==================== TENANT SCHEMAS ====================

class TenantCreate(BaseSchema):
    """Schema para criar um novo Tenant"""
    name: str = Field(..., min_length=3, max_length=100)
    slug: str = Field(..., min_length=3, max_length=50)

class TenantRead(BaseSchema, TimestampMixin):
    id: UUID
    name: str
    slug: str
    is_active: bool

# ==================== USER SCHEMAS ====================

class UserBase(BaseSchema):
    email: EmailStr = Field(..., description="Email único do usuário")
    full_name: str = Field(..., min_length=2, max_length=100)

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)
    tenant_id: Optional[UUID] = None # Opcional no registro inicial (criado no service)
    is_superuser: bool = False

    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        # Lógica de validação de força de senha aqui
        return v

class UserUpdate(BaseSchema):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    password: Optional[str] = Field(None, min_length=8, max_length=100)
    is_active: Optional[bool] = None

class UserRead(UserBase, TenantMixin, TimestampMixin):
    id: UUID
    is_active: bool
    is_superuser: bool
    last_login: Optional[datetime] = None
    
    # Padronização Pydantic V2
    model_config = ConfigDict(from_attributes=True)

class GlobalRegistration(BaseSchema):
    """Schema para o endpoint de 'Sign Up' inicial"""
    tenant: TenantCreate
    admin_user: UserCreate

# ==================== AUTH SCHEMAS ====================
class LoginRequest(BaseSchema):
    email: EmailStr
    password: str
    # ADICIONADO: Campo opcional para login em multi-tenant
    tenant_slug: Optional[str] = None 

class RefreshTokenRequest(BaseSchema):
    refresh_token: str

class TokenResponse(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserRead

class RobotCreate(BaseSchema):
    """Schema específico para criar usuários de robô via Frontend"""
    name: str = Field(..., min_length=2, description="Nome do Robô (ex: Robô Financeiro)")
    email: EmailStr = Field(..., description="Email de acesso do Robô")
    password: str = Field(..., min_length=6, description="Senha de acesso")