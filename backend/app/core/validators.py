# backend/app/core/validators.py
"""
Módulo de validadores customizados.

Fornece validadores Pydantic para:
- Expressões cron
- Semantic versioning
- Nomes de slug/identificadores
- Outros formatos específicos do domínio

Uso:
    from app.core.validators import validate_cron, validate_semver
    
    @validator('cron_expression')
    def check_cron(cls, v):
        return validate_cron(v)
"""

import re
from typing import Optional
from datetime import datetime

try:
    from croniter import croniter
    CRONITER_AVAILABLE = True
except ImportError:
    CRONITER_AVAILABLE = False


# ==================== VALIDADORES DE CRON ====================

def validate_cron(expression: str) -> str:
    """
    Valida uma expressão cron.
    
    Args:
        expression: Expressão cron (ex: '0 9 * * 1-5')
        
    Returns:
        Expressão validada
        
    Raises:
        ValueError: Se a expressão for inválida
        
    Exemplos válidos:
        - '0 9 * * *' (todo dia às 9h)
        - '*/15 * * * *' (a cada 15 minutos)
        - '0 9 * * 1-5' (9h segunda a sexta)
        - '0 0 1 * *' (primeiro dia do mês à meia-noite)
    """
    if not expression or not expression.strip():
        raise ValueError("Expressão cron não pode ser vazia")
    
    expression = expression.strip()
    
    if not CRONITER_AVAILABLE:
        # Validação básica se croniter não estiver disponível
        parts = expression.split()
        if len(parts) != 5:
            raise ValueError(
                "Expressão cron deve ter 5 campos: minuto hora dia mês dia_semana"
            )
        return expression
    
    # Validação completa com croniter
    if not croniter.is_valid(expression):
        raise ValueError(
            f"Expressão cron inválida: '{expression}'. "
            "Formato: 'minuto hora dia mês dia_semana'"
        )
    
    return expression


def get_next_cron_execution(
    expression: str,
    base_time: Optional[datetime] = None,
    timezone: str = "UTC"
) -> datetime:
    """
    Calcula a próxima execução de uma expressão cron.
    
    Args:
        expression: Expressão cron válida
        base_time: Tempo base (default: agora)
        timezone: Timezone para cálculo
        
    Returns:
        Datetime da próxima execução
        
    Raises:
        ValueError: Se croniter não estiver disponível
    """
    if not CRONITER_AVAILABLE:
        raise ValueError(
            "croniter não está instalado. Execute: pip install croniter"
        )
    
    base = base_time or datetime.utcnow()
    cron = croniter(expression, base)
    return cron.get_next(datetime)


# ==================== VALIDADORES DE VERSÃO ====================

def validate_semver(version: str) -> str:
    """
    Valida semantic versioning (semver).
    
    Formato: MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]
    
    Args:
        version: String de versão
        
    Returns:
        Versão validada
        
    Raises:
        ValueError: Se a versão for inválida
        
    Exemplos válidos:
        - '1.0.0'
        - '2.1.3'
        - '1.0.0-alpha'
        - '1.0.0-beta.1'
        - '1.0.0+20230601'
    """
    if not version or not version.strip():
        raise ValueError("Versão não pode ser vazia")
    
    version = version.strip()
    
    # Pattern semver completo
    pattern = r'^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)' \
              r'(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)' \
              r'(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?' \
              r'(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$'
    
    if not re.match(pattern, version):
        raise ValueError(
            f"Versão inválida: '{version}'. "
            "Use formato semantic versioning: MAJOR.MINOR.PATCH (ex: '1.0.0')"
        )
    
    return version


def parse_semver(version: str) -> dict:
    """
    Parse uma versão semver em componentes.
    
    Args:
        version: Versão válida (ex: '1.2.3-alpha+build')
        
    Returns:
        Dict com componentes {major, minor, patch, prerelease, build}
    """
    version = validate_semver(version)
    
    # Remove prerelease e build
    base_version = version.split('-')[0].split('+')[0]
    major, minor, patch = base_version.split('.')
    
    prerelease = None
    if '-' in version:
        prerelease = version.split('-')[1].split('+')[0]
    
    build = None
    if '+' in version:
        build = version.split('+')[1]
    
    return {
        'major': int(major),
        'minor': int(minor),
        'patch': int(patch),
        'prerelease': prerelease,
        'build': build
    }


# ==================== VALIDADORES DE SLUG ====================

def validate_slug(slug: str, max_length: int = 50) -> str:
    """
    Valida um slug (identificador URL-friendly).
    
    Regras:
    - Apenas lowercase
    - Apenas letras, números e hífens
    - Não pode começar/terminar com hífen
    - Comprimento máximo configurável
    
    Args:
        slug: String a validar
        max_length: Comprimento máximo
        
    Returns:
        Slug validado
        
    Raises:
        ValueError: Se o slug for inválido
        
    Exemplos válidos:
        - 'minha-empresa'
        - 'projeto-123'
        - 'acme-corp'
    """
    if not slug or not slug.strip():
        raise ValueError("Slug não pode ser vazio")
    
    slug = slug.strip().lower()
    
    if len(slug) > max_length:
        raise ValueError(f"Slug não pode ter mais de {max_length} caracteres")
    
    # Pattern: letras, números, hífens (não no início/fim)
    pattern = r'^[a-z0-9]+(?:-[a-z0-9]+)*$'
    
    if not re.match(pattern, slug):
        raise ValueError(
            f"Slug inválido: '{slug}'. "
            "Use apenas letras minúsculas, números e hífens (ex: 'minha-empresa')"
        )
    
    return slug


def generate_slug(text: str, max_length: int = 50) -> str:
    """
    Gera um slug a partir de texto livre.
    
    Args:
        text: Texto a converter
        max_length: Comprimento máximo
        
    Returns:
        Slug válido
        
    Exemplo:
        >>> generate_slug("Minha Empresa S/A")
        'minha-empresa-s-a'
    """
    # Remove acentos
    import unicodedata
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ascii', 'ignore').decode('ascii')
    
    # Lowercase e substitui espaços/caracteres especiais por hífen
    slug = re.sub(r'[^a-z0-9]+', '-', text.lower())
    
    # Remove hífens duplicados e das pontas
    slug = re.sub(r'-+', '-', slug).strip('-')
    
    # Trunca se necessário
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip('-')
    
    return slug


# ==================== VALIDADORES DE NOMES ====================

def validate_name(
    name: str,
    min_length: int = 2,
    max_length: int = 100,
    allow_special_chars: bool = False
) -> str:
    """
    Valida um nome (processo, agente, etc).
    
    Args:
        name: Nome a validar
        min_length: Comprimento mínimo
        max_length: Comprimento máximo
        allow_special_chars: Permitir caracteres especiais
        
    Returns:
        Nome validado
        
    Raises:
        ValueError: Se o nome for inválido
    """
    if not name or not name.strip():
        raise ValueError("Nome não pode ser vazio")
    
    name = name.strip()
    
    if len(name) < min_length:
        raise ValueError(f"Nome deve ter no mínimo {min_length} caracteres")
    
    if len(name) > max_length:
        raise ValueError(f"Nome não pode ter mais de {max_length} caracteres")
    
    if not allow_special_chars:
        # Apenas letras, números, espaços, hífens e underscores
        pattern = r'^[a-zA-Z0-9\s\-_]+$'
        if not re.match(pattern, name):
            raise ValueError(
                f"Nome inválido: '{name}'. "
                "Use apenas letras, números, espaços, hífens e underscores"
            )
    
    return name


# ==================== VALIDADORES DE IP ====================

def validate_ip_address(ip: str) -> str:
    """
    Valida endereço IP (v4 ou v6).
    
    Args:
        ip: Endereço IP
        
    Returns:
        IP validado
        
    Raises:
        ValueError: Se o IP for inválido
    """
    import ipaddress
    
    try:
        ipaddress.ip_address(ip)
        return ip
    except ValueError:
        raise ValueError(f"Endereço IP inválido: '{ip}'")


# ==================== VALIDADORES DE JSON ====================

def validate_json_keys(data: dict, required_keys: list, optional_keys: list = None) -> dict:
    """
    Valida chaves de um dict JSON.
    
    Args:
        data: Dict a validar
        required_keys: Chaves obrigatórias
        optional_keys: Chaves opcionais permitidas
        
    Returns:
        Dict validado
        
    Raises:
        ValueError: Se faltar chave obrigatória ou tiver chave inválida
    """
    if optional_keys is None:
        optional_keys = []
    
    # Verifica chaves obrigatórias
    missing = set(required_keys) - set(data.keys())
    if missing:
        raise ValueError(f"Chaves obrigatórias faltando: {missing}")
    
    # Verifica chaves extras
    allowed = set(required_keys + optional_keys)
    extra = set(data.keys()) - allowed
    if extra:
        raise ValueError(f"Chaves inválidas: {extra}")
    
    return data


# ==================== VALIDADORES DE TIMEZONE ====================

def validate_timezone(tz: str) -> str:
    """
    Valida timezone.
    
    Args:
        tz: String de timezone (ex: 'America/Sao_Paulo')
        
    Returns:
        Timezone validada
        
    Raises:
        ValueError: Se timezone for inválida
    """
    import pytz
    
    try:
        pytz.timezone(tz)
        return tz
    except pytz.exceptions.UnknownTimeZoneError:
        raise ValueError(
            f"Timezone inválida: '{tz}'. "
            "Use formato IANA (ex: 'America/Sao_Paulo', 'UTC')"
        )


# ==================== EXEMPLOS DE USO ====================

if __name__ == "__main__":
    print("🔍 Testando validadores...\n")
    
    # 1. Cron
    try:
        cron = validate_cron("0 9 * * 1-5")
        print(f"✅ Cron válido: {cron}")
    except ValueError as e:
        print(f"❌ Cron inválido: {e}")
    
    # 2. Semver
    try:
        version = validate_semver("1.2.3-alpha+build")
        parsed = parse_semver(version)
        print(f"✅ Versão válida: {version}")
        print(f"   Parsed: {parsed}")
    except ValueError as e:
        print(f"❌ Versão inválida: {e}")
    
    # 3. Slug
    try:
        slug = generate_slug("Minha Empresa S/A")
        print(f"✅ Slug gerado: {slug}")
    except ValueError as e:
        print(f"❌ Erro no slug: {e}")
    
    # 4. Nome
    try:
        name = validate_name("Processo_Teste_01")
        print(f"✅ Nome válido: {name}")
    except ValueError as e:
        print(f"❌ Nome inválido: {e}")
    
    print("\n✅ Testes concluídos!")