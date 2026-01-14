"""
Endpoints de autenticação e gestão de usuários (Onboarding e Login).

Rotas:
- POST /auth/register     → Onboarding (Cria Tenant + Usuário Admin)
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
    GlobalRegistration,
    RobotCreate,
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
    stmt = select(Tenant).where(Tenant.slug == slug)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Onboarding (Criar Empresa e Admin)",
    description="Cria um novo Tenant (Empresa) e o primeiro Usuário Admin."
)
async def register(
    payload: GlobalRegistration, # <--- CORREÇÃO: Aceita a estrutura completa
    session: AsyncSession = Depends(get_session)
) -> User:
    """
    Realiza o cadastro inicial (Sign Up).
    
    Processo:
    1. Verifica se o Slug do Tenant já existe.
    2. Cria o Tenant.
    3. Cria o Usuário Admin vinculado a este Tenant.
    """
    logger.info(f"Starting onboarding for tenant: {payload.tenant.name}")
    
    # 1. Validar se o Tenant Slug já existe (Deve ser único globalmente)
    existing_tenant = await get_tenant_by_slug(session, payload.tenant.slug)
    if existing_tenant:
        raise ConflictError(
            message=f"O identificador da empresa '{payload.tenant.slug}' já está em uso.",
            details={"field": "tenant.slug"}
        )
    
    # 2. Criar o Tenant
    new_tenant = Tenant(
        name=payload.tenant.name,
        slug=payload.tenant.slug,
        is_active=True
    )
    session.add(new_tenant)
    
    # Flush para gerar o ID do tenant (necessário para criar o usuário)
    await session.flush()
    
    # 3. Validar se email já existe NESTE novo tenant (redundante pois é novo, mas boa prática)
    # Nota: Em sistemas multi-tenant, o mesmo email pode existir em tenants diferentes.
    # Se você quiser unicidade global de email, a validação seria aqui.
    
    # 4. Criar o Usuário Admin
    new_user = User(
        tenant_id=new_tenant.id,
        email=payload.admin_user.email,
        full_name=payload.admin_user.full_name,
        hashed_password=hash_password(payload.admin_user.password),
        is_active=True,
        is_superuser=payload.admin_user.is_superuser # Geralmente True para o primeiro user
    )
    
    session.add(new_user)
    
    try:
        await session.commit()
        await session.refresh(new_user)
        logger.info(f"Onboarding completed. Tenant: {new_tenant.id}, User: {new_user.id}")
        return new_user
        
    except Exception as e:
        await session.rollback()
        logger.error(f"Onboarding failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Falha ao criar conta. Tente novamente."
        )


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login",
    description="Autentica usuário e retorna tokens JWT."
)
async def login(
    credentials: LoginRequest,
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    logger.info(f"Login attempt for: {credentials.email}")
    
    # 1. Resolver Tenant (Opcional ou Obrigatório dependendo da regra de negócio)
    tenant_id = None
    if credentials.tenant_slug:
        tenant = await get_tenant_by_slug(session, credentials.tenant_slug)
        if not tenant:
            raise AuthenticationError(
                message="Credenciais inválidas",
                details={"reason": "Empresa não encontrada"}
            )
        tenant_id = str(tenant.id)
    
    # 2. Buscar Usuário
    user = await get_user_by_email(session, credentials.email, tenant_id)
    
    # 3. Validações de Segurança (Timing Attack safe)
    if not user or not verify_password(credentials.password, user.hashed_password):
        logger.warning(f"Login failed: invalid credentials - {credentials.email}")
        raise AuthenticationError(
            message="Credenciais inválidas",
            details={"reason": "Email ou senha incorretos"}
        )
    
    if not user.is_active:
        raise AuthenticationError(
            message="Usuário inativo",
            details={"reason": "Conta desativada."}
        )
    
    # 4. Atualizar metadados
    user.last_login = datetime.utcnow()
    await session.commit()
    await session.refresh(user) # <--- ADICIONE ESTA LINHA OBRIGATORIAMENTE
    
    # 5. Gerar Tokens
    tokens = create_tokens_for_user(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        additional_claims={
            "email": user.email,
            "is_superuser": user.is_superuser
        }
    )
    
    return {
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "token_type": tokens["token_type"],
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": user
    }


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Renovar Token"
)
async def refresh_token(
    token_data: RefreshTokenRequest,
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    try:
        payload = decode_token(token_data.refresh_token)
    except Exception as e:
        raise AuthenticationError(
            message="Token inválido ou expirado",
            details={"error": str(e)}
        )
    
    if payload.get("type") != "refresh":
        raise AuthenticationError(message="Token inválido")
    
    user_id = payload.get("sub")
    
    stmt = select(User).where(User.id == user_id, User.deleted_at.is_(None))
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        raise AuthenticationError(message="Usuário não encontrado ou inativo")
    
    tokens = create_tokens_for_user(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        additional_claims={
            "email": user.email,
            "is_superuser": user.is_superuser
        }
    )
    
    return {
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "token_type": tokens["token_type"],
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": user
    }


@router.get("/me", response_model=UserRead)
async def get_current_user(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session)
) -> User:
    stmt = select(User).where(User.id == user_id, User.deleted_at.is_(None))
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise NotFoundError(resource="User", identifier=user_id)
    return user


@router.put("/me", response_model=UserRead)
async def update_current_user(
    user_data: UserUpdate,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session)
) -> User:
    stmt = select(User).where(User.id == user_id, User.deleted_at.is_(None))
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise NotFoundError(resource="User", identifier=user_id)
    
    if user_data.email and user_data.email != user.email:
        existing = await get_user_by_email(session, user_data.email, str(user.tenant_id))
        if existing and existing.id != user.id:
            raise ConflictError(message=f"Email '{user_data.email}' já está em uso")
        user.email = user_data.email
    
    if user_data.full_name:
        user.full_name = user_data.full_name
    
    if user_data.password:
        user.hashed_password = hash_password(user_data.password)
    
    if user_data.is_active is not None:
        user.is_active = user_data.is_active
    
    await session.commit()
    await session.refresh(user)
    return user

@router.post(
    "/register-robot",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Criar Usuário de Robô",
    description="Cria um usuário para o robô vinculado ao tenant do admin logado."
)
async def register_robot(
    data: RobotCreate,
    current_user: User = Depends(get_current_user), # Exige autenticação
    session: AsyncSession = Depends(get_session)
):
    # 1. Verifica se email já existe
    existing_user = await get_user_by_email(session, data.email)
    if existing_user:
        raise ConflictError(
            message=f"O email '{data.email}' já está em uso.",
            details={"field": "email"}
        )

    # 2. Cria o usuário vinculado ao MESMO tenant do admin
    # Nota: is_superuser=False pois robôs não devem administrar o painel
    new_robot = User(
        email=data.email,
        full_name=data.name,
        hashed_password=hash_password(data.password),
        tenant_id=current_user.tenant_id, 
        is_active=True,
        is_superuser=False
    )
    
    session.add(new_robot)
    await session.commit()
    await session.refresh(new_robot)
    
    logger.info(f"Robot user created: {new_robot.email} for tenant {current_user.tenant_id}")
    
    return new_robot