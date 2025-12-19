"""
Endpoints de autenticação e gestão de usuários.

Rotas:
- POST /auth/register     → Criar novo usuário
- POST /auth/login        → Login com email/password
- POST /auth/refresh      → Renovar access_token
- GET  /auth/me           → Dados do usuário atual
- PUT  /auth/me           → Atualizar dados do usuário atual
"""

from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.database import get_session
from app.core.config import settings
from app.core.security import (
    hash_password,
    verify_password,
    create_tokens_for_user,
    decode_token,
    get_current_user_id,
)
from app.core.exceptions import (
    AuthenticationError,
    NotFoundError,
    ConflictError,
)
from app.core.logging import get_logger
from app.models import User, Tenant
from app.schemas.auth import (
    UserCreate,
    UserRead,
    UserUpdate,
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    TenantRead,
)


logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def get_user_by_email(
    session: AsyncSession,
    email: str,
    tenant_id: str = None
) -> User | None:
    """Busca usuário por email (opcionalmente filtrado por tenant)"""
    stmt = select(User).where(
        User.email == email,
        User.deleted_at.is_(None)
    )
    
    if tenant_id:
        stmt = stmt.where(User.tenant_id == tenant_id)
    
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_tenant_by_slug(session: AsyncSession, slug: str) -> Tenant | None:
    """Busca tenant por slug"""
    stmt = select(Tenant).where(
        Tenant.slug == slug,
        Tenant.is_active == True
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar Novo Usuário",
    description="Cria um novo usuário no sistema. Requer tenant_id válido."
)
async def register(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_session)
) -> User:
    """
    Registra novo usuário.
    
    Validações:
    - Email único por tenant
    - Tenant deve existir e estar ativo
    - Senha atende requisitos de segurança (validado no schema)
    """
    logger.info(f"Registering new user: {user_data.email}")
    
    # Validar se tenant existe
    if user_data.tenant_id:
        stmt = select(Tenant).where(
            Tenant.id == user_data.tenant_id,
            Tenant.is_active == True
        )
        result = await session.execute(stmt)
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            raise NotFoundError(
                resource="Tenant",
                identifier=str(user_data.tenant_id),
                details={"reason": "Tenant não encontrado ou inativo"}
            )
    else:
        # TODO: Em produção, definir lógica de auto-atribuição de tenant
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tenant_id é obrigatório"
        )
    
    # Verificar se email já existe no tenant
    existing_user = await get_user_by_email(
        session,
        user_data.email,
        str(user_data.tenant_id)
    )
    
    if existing_user:
        raise ConflictError(
            message=f"Email '{user_data.email}' já está cadastrado neste tenant",
            details={"email": user_data.email}
        )
    
    # Criar usuário
    user = User(
        tenant_id=user_data.tenant_id,
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hash_password(user_data.password),
        is_active=True,
        is_superuser=user_data.is_superuser
    )
    
    session.add(user)
    await session.commit()
    await session.refresh(user)
    
    logger.info(f"User registered successfully: {user.id}")
    
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login",
    description="Autentica usuário e retorna tokens JWT (access + refresh)."
)
async def login(
    credentials: LoginRequest,
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """
    Autentica usuário e gera tokens JWT.
    
    Validações:
    - Email deve existir
    - Senha deve estar correta
    - Usuário deve estar ativo
    - Tenant deve estar ativo (se especificado)
    """
    logger.info(f"Login attempt for: {credentials.email}")
    
    # Buscar tenant se slug foi fornecido
    tenant_id = None
    if credentials.tenant_slug:
        tenant = await get_tenant_by_slug(session, credentials.tenant_slug)
        if not tenant:
            raise AuthenticationError(
                message="Credenciais inválidas",
                details={"reason": "Tenant não encontrado"}
            )
        tenant_id = str(tenant.id)
    
    # Buscar usuário
    user = await get_user_by_email(session, credentials.email, tenant_id)
    
    if not user:
        logger.warning(f"Login failed: user not found - {credentials.email}")
        raise AuthenticationError(
            message="Credenciais inválidas",
            details={"reason": "Email ou senha incorretos"}
        )
    
    # Verificar senha
    if not verify_password(credentials.password, user.hashed_password):
        logger.warning(f"Login failed: invalid password - {credentials.email}")
        raise AuthenticationError(
            message="Credenciais inválidas",
            details={"reason": "Email ou senha incorretos"}
        )
    
    # Verificar se usuário está ativo
    if not user.is_active:
        logger.warning(f"Login failed: inactive user - {credentials.email}")
        raise AuthenticationError(
            message="Usuário inativo",
            details={"reason": "Conta desativada. Contate o administrador."}
        )
    
    # Atualizar last_login
    user.last_login = datetime.utcnow()
    await session.commit()
    
    # Gerar tokens
    tokens = create_tokens_for_user(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        additional_claims={
            "email": user.email,
            "is_superuser": user.is_superuser
        }
    )
    
    logger.info(f"Login successful: {user.id}")
    
    # Preparar response
    return {
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "token_type": tokens["token_type"],
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # em segundos
        "user": user
    }


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Renovar Token",
    description="Renova access_token usando refresh_token válido."
)
async def refresh_token(
    token_data: RefreshTokenRequest,
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """
    Renova access_token usando refresh_token.
    
    Validações:
    - Refresh token deve ser válido
    - Usuário deve existir e estar ativo
    """
    logger.info("Token refresh attempt")
    
    # Decodificar refresh token
    try:
        payload = decode_token(token_data.refresh_token)
    except Exception as e:
        logger.warning(f"Invalid refresh token: {str(e)}")
        raise AuthenticationError(
            message="Token inválido ou expirado",
            details={"error": str(e)}
        )
    
    # Verificar tipo do token
    if payload.get("type") != "refresh":
        raise AuthenticationError(
            message="Token inválido",
            details={"reason": "Esperado refresh token"}
        )
    
    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")
    
    # Buscar usuário
    stmt = select(User).where(
        User.id == user_id,
        User.deleted_at.is_(None)
    )
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        raise AuthenticationError(
            message="Usuário não encontrado ou inativo",
            details={"user_id": str(user_id)}
        )
    
    # Gerar novos tokens
    tokens = create_tokens_for_user(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        additional_claims={
            "email": user.email,
            "is_superuser": user.is_superuser
        }
    )
    
    logger.info(f"Token refreshed successfully: {user.id}")
    
    return {
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "token_type": tokens["token_type"],
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": user
    }


@router.get(
    "/me",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Usuário Atual",
    description="Retorna dados do usuário autenticado."
)
async def get_current_user(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session)
) -> User:
    """
    Retorna dados do usuário autenticado.
    
    Requer: Token JWT válido no header Authorization
    """
    stmt = select(User).where(
        User.id == user_id,
        User.deleted_at.is_(None)
    )
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise NotFoundError(
            resource="User",
            identifier=user_id
        )
    
    return user


@router.put(
    "/me",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Atualizar Usuário Atual",
    description="Atualiza dados do usuário autenticado."
)
async def update_current_user(
    user_data: UserUpdate,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session)
) -> User:
    """
    Atualiza dados do usuário autenticado.
    
    Campos atualizáveis:
    - email (deve ser único no tenant)
    - full_name
    - password (será hasheada)
    """
    # Buscar usuário
    stmt = select(User).where(
        User.id == user_id,
        User.deleted_at.is_(None)
    )
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise NotFoundError(
            resource="User",
            identifier=user_id
        )
    
    # Atualizar campos (apenas se fornecidos)
    if user_data.email and user_data.email != user.email:
        # Verificar se novo email já existe no tenant
        existing = await get_user_by_email(
            session,
            user_data.email,
            str(user.tenant_id)
        )
        if existing and existing.id != user.id:
            raise ConflictError(
                message=f"Email '{user_data.email}' já está em uso",
                details={"email": user_data.email}
            )
        user.email = user_data.email
    
    if user_data.full_name:
        user.full_name = user_data.full_name
    
    if user_data.password:
        user.hashed_password = hash_password(user_data.password)
    
    if user_data.is_active is not None:
        user.is_active = user_data.is_active
    
    # Atualizar updated_at (automático via SQLModel)
    await session.commit()
    await session.refresh(user)
    
    logger.info(f"User updated: {user.id}")
    
    return user
