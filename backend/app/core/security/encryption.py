# backend/app/core/security/encryption.py
"""
Módulo de criptografia de credenciais sensíveis.

Fornece helpers para:
- Criptografia/descriptografia de credenciais (Fernet/AES-256)
- Rotação de chaves de criptografia
- Mascaramento de valores sensíveis
- Geração de tokens seguros

IMPORTANTE: Este módulo lida com CRIPTOGRAFIA de dados (reversível).
Para hash de SENHAS (irreversível), use app.core.security.password

Uso:
    from app.core.security.encryption import encrypt_credential, decrypt_credential
    
    # Criptografar credencial
    encrypted = encrypt_credential("minha_api_key_secreta")
    
    # Descriptografar credencial
    decrypted = decrypt_credential(encrypted)
"""

import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken


# ==================== CONFIGURAÇÃO ====================

# Chave de criptografia Fernet (AES-256)
# IMPORTANTE: Em produção, armazenar em variável de ambiente ou secret manager
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

if not ENCRYPTION_KEY:
    # Gera chave temporária em desenvolvimento
    # Em produção, SEMPRE usar chave fixa de variável de ambiente
    print("⚠️  WARNING: ENCRYPTION_KEY não encontrada. Gerando chave temporária.")
    print("⚠️  Em produção, configure a variável ENCRYPTION_KEY!")
    ENCRYPTION_KEY = Fernet.generate_key().decode()

# Instância Fernet
_fernet = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)


# ==================== CRIPTOGRAFIA DE CREDENCIAIS ====================

def encrypt_credential(plaintext: str) -> str:
    """
    Criptografa uma credencial usando Fernet (AES-256).
    
    Use para: API keys, tokens, senhas de sistemas externos, certificados
    NÃO use para: senhas de usuários (use hash_password de password.py)
    
    Args:
        plaintext: Texto em claro a ser criptografado
        
    Returns:
        String criptografada (base64)
        
    Exemplo:
        >>> encrypted = encrypt_credential("sk_live_123abc...")
        >>> print(encrypted)
        'gAAAAABh...'
    """
    if not plaintext:
        raise ValueError("Texto a criptografar não pode ser vazio")
    
    encrypted_bytes = _fernet.encrypt(plaintext.encode())
    return encrypted_bytes.decode()


def decrypt_credential(encrypted: str) -> str:
    """
    Descriptografa uma credencial criptografada com Fernet.
    
    Args:
        encrypted: String criptografada (base64)
        
    Returns:
        Texto em claro
        
    Raises:
        InvalidToken: Se o token for inválido ou corrompido
        ValueError: Se a chave de criptografia estiver incorreta
        
    Exemplo:
        >>> decrypted = decrypt_credential('gAAAAABh...')
        >>> print(decrypted)
        'sk_live_123abc...'
    """
    if not encrypted:
        raise ValueError("Texto criptografado não pode ser vazio")
    
    try:
        decrypted_bytes = _fernet.decrypt(encrypted.encode())
        return decrypted_bytes.decode()
    except InvalidToken:
        raise ValueError("Token de criptografia inválido ou corrompido")


def rotate_encryption_key(
    old_encrypted: str,
    old_key: str,
    new_key: Optional[str] = None
) -> str:
    """
    Rotaciona a chave de criptografia de uma credencial.
    
    Descriptografa com a chave antiga e re-criptografa com a nova.
    
    Args:
        old_encrypted: Credencial criptografada com chave antiga
        old_key: Chave antiga (base64)
        new_key: Nova chave (base64). Se None, usa a chave atual do sistema
        
    Returns:
        Credencial re-criptografada com a nova chave
        
    Exemplo:
        >>> rotated = rotate_encryption_key(
        ...     old_encrypted='gAAAAABh...',
        ...     old_key='old_key_here',
        ...     new_key='new_key_here'
        ... )
    """
    # Descriptografa com chave antiga
    old_fernet = Fernet(old_key.encode() if isinstance(old_key, str) else old_key)
    plaintext = old_fernet.decrypt(old_encrypted.encode()).decode()
    
    # Re-criptografa com chave nova
    if new_key:
        new_fernet = Fernet(new_key.encode() if isinstance(new_key, str) else new_key)
        return new_fernet.encrypt(plaintext.encode()).decode()
    else:
        return encrypt_credential(plaintext)


# ==================== TOKENS SEGUROS ====================

def generate_secure_token(length: int = 32) -> str:
    """
    Gera um token aleatório seguro (hex).
    
    Use para: tokens de API, session IDs, correlation IDs
    
    Args:
        length: Número de bytes (resultado será length*2 caracteres hex)
        
    Returns:
        Token hexadecimal
        
    Exemplo:
        >>> token = generate_secure_token(16)
        >>> print(len(token))
        32
    """
    return os.urandom(length).hex()


# ==================== UTILITÁRIOS ====================

def generate_new_encryption_key() -> str:
    """
    Gera uma nova chave Fernet (AES-256).
    
    Útil para setup inicial ou rotação de chaves.
    
    Returns:
        Chave Fernet em base64
        
    Exemplo:
        >>> key = generate_new_encryption_key()
        >>> print(key)
        'abcd1234...'
    """
    return Fernet.generate_key().decode()


def mask_credential(value: str, visible_chars: int = 4) -> str:
    """
    Mascara uma credencial para exibição segura.
    
    Use para: logs, exibição em UI, auditoria
    
    Args:
        value: Valor a ser mascarado
        visible_chars: Número de caracteres visíveis no final
        
    Returns:
        String mascarada
        
    Exemplo:
        >>> masked = mask_credential("sk_live_123abc456def", 4)
        >>> print(masked)
        '******************6def'
    """
    if not value or len(value) <= visible_chars:
        return "*" * 8
    
    visible_part = value[-visible_chars:]
    masked_part = "*" * (len(value) - visible_chars)
    return masked_part + visible_part


# ==================== VALIDAÇÕES ====================

def validate_encryption_key(key: str) -> bool:
    """
    Valida se uma chave Fernet é válida.
    
    Args:
        key: Chave a ser validada
        
    Returns:
        True se válida, False caso contrário
    """
    try:
        Fernet(key.encode() if isinstance(key, str) else key)
        return True
    except Exception:
        return False


# ==================== EXEMPLOS DE USO ====================

if __name__ == "__main__":
    # Teste básico
    print("🔐 Testando criptografia de credenciais...\n")
    
    # 1. Criptografar API key
    api_key = "sk_live_1234567890abcdef"
    encrypted = encrypt_credential(api_key)
    print(f"Original:      {api_key}")
    print(f"Criptografada: {encrypted}")
    print(f"Mascarada:     {mask_credential(encrypted)}")
    
    # 2. Descriptografar
    decrypted = decrypt_credential(encrypted)
    print(f"Descriptografada: {decrypted}")
    print(f"Match: {api_key == decrypted}\n")
    
    # 3. Token seguro
    token = generate_secure_token(16)
    print(f"Token gerado: {token}")
    
    print("\n✅ Testes concluídos!")