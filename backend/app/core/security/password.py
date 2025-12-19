# backend/app/core/security/password.py
"""
Módulo centralizado de hashing de senhas.

Evita duplicação de código entre auth.py e encryption.py.
Usa bcrypt para hashing seguro.
"""

from passlib.context import CryptContext


# ==================== CONFIGURAÇÃO ====================

# Context para hashing de senhas (bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ==================== OPERAÇÕES DE SENHA ====================

def hash_password(password: str) -> str:
    """
    Gera hash bcrypt de uma senha.
    
    Args:
        password: Senha em texto claro
        
    Returns:
        Hash bcrypt da senha
        
    Exemplo:
        >>> hashed = hash_password("minha_senha123")
        >>> print(hashed)
        '$2b$12$...'
    """
    if not password:
        raise ValueError("Senha não pode ser vazia")
    
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica se uma senha corresponde ao hash.
    
    Args:
        plain_password: Senha em texto claro
        hashed_password: Hash bcrypt para comparar
        
    Returns:
        True se a senha está correta, False caso contrário
        
    Exemplo:
        >>> is_valid = verify_password("minha_senha123", hashed)
        >>> print(is_valid)
        True
    """
    if not plain_password or not hashed_password:
        return False
    
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Alias para hash_password (compatibilidade).
    
    Args:
        password: Senha em texto claro
        
    Returns:
        Hash bcrypt da senha
    """
    return hash_password(password)