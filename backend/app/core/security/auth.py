# backend/app/core/security/auth.py
"""
[FIX #3] Sistema de autenticação e autorização com JWT.
Suporta access tokens e refresh tokens com multi-tenancy.

FIX: get_current_tenant_id() agora extrai tenant_id do JWT (sem query ao BD)
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID
from jose import JWTError, jwt
from fastapi import Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings
from app.core.exceptions import AuthenticationError, AuthorizationError, TenantError
from app.core.logging import get_logger
from app.core.security.password import hash_password, verify_password


logger = get_logger(__name__)

# Security scheme para documentação automática
security = HTTPBearer()


# ============================================================================
# JWT TOKEN OPERATIONS
# ============================================================================

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Cria um access token JWT.
    
    Args:
        data: Dados a serem incluídos no token (user_id, tenant_id, etc.)
        expires_delta: Tempo de expiração customizado
    
    Returns:
        Token JWT assinado
    """
    to_encode = data.copy()
    
    # Define expiração
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })
    
    # Assina o token
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Cria um refresh token JWT.
    
    Args:
        data: Dados a serem incluídos no token (user_id, tenant_id)
        expires_delta: Tempo de expiração customizado
    
    Returns:
        Refresh token JWT assinado
    """
    to_encode = data.copy()
    
    # Define expiração (mais longa que access token)
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    })
    
    # Assina o token
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decodifica e valida um token JWT.
    
    Args:
        token: Token JWT a ser decodificado
    
    Returns:
        Payload do token
    
    Raises:
        AuthenticationError: Se o token for inválido ou expirado
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError as e:
        logger.warning(f"Invalid JWT token: {str(e)}")
        raise AuthenticationError(
            message="Token inválido ou expirado",
            details={"error": str(e)}
        )


def verify_token_type(payload: Dict[str, Any], expected_type: str) -> None:
    """
    Verifica se o token é do tipo esperado.
    
    Args:
        payload: Payload decodificado do token
        expected_type: Tipo esperado ('access' ou 'refresh')
    
    Raises:
        AuthenticationError: Se o tipo não corresponder
    """
    token_type = payload.get("type")
    if token_type != expected_type:
        raise AuthenticationError(
            message=f"Token inválido. Esperado tipo '{expected_type}', recebido '{token_type}'",
            details={"expected": expected_type, "received": token_type}
        )


# ============================================================================
# AUTHENTICATION DEPENDENCIES
# ============================================================================

async def get_current_user_payload(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Extrai e valida o payload do usuário atual do token JWT.
    
    Args:
        credentials: Credenciais HTTP Bearer extraídas do header
    
    Returns:
        Payload do token contendo user_id, tenant_id, etc.
    
    Raises:
        AuthenticationError: Se o token for inválido
    """
    token = credentials.credentials
    payload = decode_token(token)
    
    # Verifica se é um access token
    verify_token_type(payload, "access")
    
    # Valida campos obrigatórios
    user_id = payload.get("sub")  # 'sub' é o padrão JWT para subject (user_id)
    
    if not user_id:
        raise AuthenticationError(
            message="Token inválido: usuário não identificado",
            details={"missing_field": "sub"}
        )
    
    return payload


async def get_current_user_id(
    payload: Dict[str, Any] = Depends(get_current_user_payload)
) -> str:
    """
    Extrai o ID do usuário atual.
    
    Args:
        payload: Payload do token JWT
    
    Returns:
        ID do usuário
    """
    return payload["sub"]


async def get_current_tenant_id(
    payload: Dict[str, Any] = Depends(get_current_user_payload)
) -> UUID:
    """
    [FIX #3] Extrai o tenant_id do usuário atual DO JWT.
    
    ✅ SEM query ao BD (performance otimizada)
    
    Args:
        payload: Payload do token JWT
    
    Returns:
        ID do tenant
    
    Raises:
        TenantError: Se tenant_id não estiver presente no JWT
    """
    tenant_id = payload.get("tenant_id")
    
    if not tenant_id:
        raise TenantError(
            message="Token inválido: tenant não identificado",
            details={"missing_field": "tenant_id"}
        )
    
    try:
        return UUID(tenant_id)
    except (ValueError, TypeError):
        raise TenantError(
            message="Token inválido: tenant_id malformado",
            details={"tenant_id": tenant_id}
        )


# ============================================================================
# OPTIONAL AUTHENTICATION
# ============================================================================

async def get_optional_tenant_id(
    x_tenant_id: Optional[str] = Header(None, alias=settings.TENANT_HEADER_NAME)
) -> Optional[str]:
    """
    Extrai tenant_id do header para rotas públicas (opcional).
    
    Usado em rotas que não requerem autenticação mas podem usar tenant_id.
    Exemplo: health check detalhado por tenant.
    
    Args:
        x_tenant_id: Tenant ID passado no header
    
    Returns:
        Tenant ID ou None
    """
    return x_tenant_id


# ============================================================================
# AUTHORIZATION HELPERS
# ============================================================================

def check_permission(
    user_payload: Dict[str, Any],
    required_permission: str
) -> None:
    """
    Verifica se o usuário tem a permissão necessária.
    
    Args:
        user_payload: Payload do token do usuário
        required_permission: Permissão necessária
    
    Raises:
        AuthorizationError: Se o usuário não tiver a permissão
    """
    user_permissions = user_payload.get("permissions", [])
    
    if required_permission not in user_permissions:
        raise AuthorizationError(
            message="Acesso negado: permissão insuficiente",
            details={
                "required_permission": required_permission,
                "user_permissions": user_permissions
            }
        )


def check_tenant_access(
    user_tenant_id: UUID,
    resource_tenant_id: UUID
) -> None:
    """
    Verifica se o usuário tem acesso ao tenant do recurso.
    
    Args:
        user_tenant_id: Tenant ID do usuário
        resource_tenant_id: Tenant ID do recurso sendo acessado
    
    Raises:
        AuthorizationError: Se os tenants não corresponderem
    """
    if user_tenant_id != resource_tenant_id:
        raise AuthorizationError(
            message="Acesso negado: recurso pertence a outra organização",
            details={
                "user_tenant": str(user_tenant_id),
                "resource_tenant": str(resource_tenant_id)
            }
        )


# ============================================================================
# TOKEN GENERATION HELPERS
# ============================================================================

def create_tokens_for_user(
    user_id: str,
    tenant_id: str,
    additional_claims: Optional[Dict[str, Any]] = None
) -> Dict[str, str]:
    """
    Cria access e refresh tokens para um usuário.
    
    Args:
        user_id: ID do usuário
        tenant_id: ID do tenant
        additional_claims: Claims adicionais (roles, permissions, etc.)
    
    Returns:
        Dict com access_token e refresh_token
    """
    # Dados base do token
    token_data = {
        "sub": user_id,
        "tenant_id": tenant_id,  # ← IMPORTANTE: tenant_id vai no JWT
    }
    
    # Adiciona claims extras se fornecidos
    if additional_claims:
        token_data.update(additional_claims)
    
    # Gera tokens
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token({"sub": user_id, "tenant_id": tenant_id})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


# ============================================================================
# PASSWORD OPERATIONS (RE-EXPORTADOS PARA COMPATIBILIDADE)
# ============================================================================

__all__ = [
    'hash_password',
    'verify_password',
    'create_access_token',
    'create_refresh_token',
    'decode_token',
    'verify_token_type',
    'get_current_user_payload',
    'get_current_user_id',
    'get_current_tenant_id',  # ← [FIX #3] Usar este!
    'get_optional_tenant_id',
    'check_permission',
    'check_tenant_access',
    'create_tokens_for_user',
    'security'
]