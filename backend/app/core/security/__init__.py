# backend/app/core/security/__init__.py
"""
Módulo de segurança do Orquestrador RPA.

Fornece:
- Autenticação e autorização JWT (auth.py)
- Criptografia de credenciais (encryption.py)
- Hashing de senhas (password.py)
- Validadores customizados (validators.py)

Uso:
    # Autenticação
    from app.core.security import create_access_token, verify_password
    
    # Criptografia de credenciais
    from app.core.security import encrypt_credential, decrypt_credential
    
    # Validadores
    from app.core.security import validate_cron, validate_semver
"""

# ==================== AUTENTICAÇÃO E AUTORIZAÇÃO ====================
from .auth import (
    # JWT Operations
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_token_type,
    # FastAPI Dependencies
    get_current_user_payload,
    get_current_user_id,
    get_current_tenant_id,
    get_optional_tenant_id,
    security,
    # Authorization
    check_permission,
    check_tenant_access,
    # Token Generation
    create_tokens_for_user,
)

# ==================== HASH DE SENHAS ====================
from .password import (
    hash_password,
    verify_password,
    get_password_hash,  # Alias
)

# ==================== CRIPTOGRAFIA DE CREDENCIAIS ====================
from .encryption import (
    encrypt_credential,
    decrypt_credential,
    rotate_encryption_key,
    generate_secure_token,
    generate_new_encryption_key,
    mask_credential,
    validate_encryption_key,
)

# ==================== VALIDADORES ====================
from ..validators import (
    # Cron
    validate_cron,
    get_next_cron_execution,
    # Versioning
    validate_semver,
    parse_semver,
    # Slug
    validate_slug,
    generate_slug,
    # Name
    validate_name,
    # Network
    validate_ip_address,
    # JSON
    validate_json_keys,
    # Timezone
    validate_timezone,
)


# ==================== EXPORTAÇÕES ====================
__all__ = [
    # Auth
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "verify_token_type",
    "get_current_user_payload",
    "get_current_user_id",
    "get_current_tenant_id",
    "get_optional_tenant_id",
    "security",
    "check_permission",
    "check_tenant_access",
    "create_tokens_for_user",
    
    # Password
    "hash_password",
    "verify_password",
    "get_password_hash",
    
    # Encryption
    "encrypt_credential",
    "decrypt_credential",
    "rotate_encryption_key",
    "generate_secure_token",
    "generate_new_encryption_key",
    "mask_credential",
    "validate_encryption_key",
    
    # Validators
    "validate_cron",
    "get_next_cron_execution",
    "validate_semver",
    "parse_semver",
    "validate_slug",
    "generate_slug",
    "validate_name",
    "validate_ip_address",
    "validate_json_keys",
    "validate_timezone",
]