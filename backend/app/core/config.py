# backend/app/core/config.py
"""
Configurações centralizadas da aplicação usando Pydantic Settings.
Todas as variáveis de ambiente são validadas e tipadas.
"""
from typing import List, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """
    Configurações da aplicação carregadas de variáveis de ambiente.
    Usa Pydantic para validação automática e type safety.
    """
    
    # === API Configuration ===
    APP_NAME: str = "RPA Orchestrator API"
    APP_DESCRIPTION: str = "Plataforma de Orquestração de Automações RPA Multi-Tenant"
    API_VERSION: str = "v1"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development, staging, production
    
    # === Server Configuration ===
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # === Database Configuration ===
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 40
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 3600  # 1 hora
    
    # === Redis Configuration ===
    REDIS_URL: str
    REDIS_MAX_CONNECTIONS: int = 50
    REDIS_DECODE_RESPONSES: bool = True
    
    # === Security Configuration ===
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # === CORS Configuration ===
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]
    
    # === Logging Configuration ===
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json ou text
    
    # === Multi-Tenant Configuration ===
    DEFAULT_TENANT_ID: str = "default"
    TENANT_HEADER_NAME: str = "X-Tenant-ID"
    
    # === Cache Configuration ===
    CACHE_TTL_SECONDS: int = 300  # 5 minutos padrão
    CACHE_ENABLED: bool = True
    
    # === Rate Limiting ===
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 100
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Valida que a SECRET_KEY tem tamanho mínimo seguro."""
        if len(v) < 32:
            raise ValueError("SECRET_KEY deve ter pelo menos 32 caracteres")
        return v
    
    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Valida que o ambiente é válido."""
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"ENVIRONMENT deve ser um de: {allowed}")
        return v
    
    @property
    def is_development(self) -> bool:
        """Verifica se está em ambiente de desenvolvimento."""
        return self.ENVIRONMENT == "development"
    
    @property
    def is_production(self) -> bool:
        """Verifica se está em ambiente de produção."""
        return self.ENVIRONMENT == "production"
    
    @property
    def api_prefix(self) -> str:
        """Retorna o prefixo da API com versionamento."""
        return f"/api/{self.API_VERSION}"


@lru_cache()
def get_settings() -> Settings:
    """
    Retorna uma instância singleton das configurações.
    Usa lru_cache para garantir que seja criada apenas uma vez.
    """
    return Settings()


# Instância global para facilitar imports
settings = get_settings()