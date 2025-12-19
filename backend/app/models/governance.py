# backend/app/models/governance.py
"""
MÃ³dulo de governanÃ§a e seguranÃ§a.

Define:
- Asset: VariÃ¡veis/configuraÃ§Ãµes do sistema
- Credencial: Credenciais criptografadas
- Agendamento: Agendamentos cron de processos
"""

from datetime import datetime
from enum import Enum
from typing import Optional, TYPE_CHECKING
from uuid import UUID

from sqlmodel import Field, Relationship, Column, String, JSON, Index
from pydantic import field_validator

from .base import BaseModel

if TYPE_CHECKING:
    from .core import Processo


# ==================== ENUMS ====================

class TipoAssetEnum(str, Enum):
    """Tipo de asset/variÃ¡vel."""
    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    JSON = "json"
    ENCRYPTED = "encrypted"  # Valor sensÃ­vel criptografado


class ScopeAssetEnum(str, Enum):
    """Escopo de visibilidade do asset."""
    GLOBAL = "global"      # VisÃ­vel para todos os processos
    PROCESSO = "processo"  # EspecÃ­fico de um processo


class TipoCredencialEnum(str, Enum):
    """Tipo de credencial."""
    BASIC_AUTH = "basic_auth"
    API_KEY = "api_key"
    OAUTH2 = "oauth2"
    CERTIFICATE = "certificate"
    CUSTOM = "custom"


# ==================== MODELOS ====================

class Asset(BaseModel, table=True):
    """
    Representa uma variÃ¡vel/configuraÃ§Ã£o do sistema.
    
    Assets podem ser:
    - Globais (acessÃ­veis por todos os processos)
    - EspecÃ­ficos de processo
    - Criptografados (para dados sensÃ­veis)
    """
    
    __tablename__ = "asset"
    
    # IdentificaÃ§Ã£o
    name: str = Field(
        max_length=100,
        index=True,
        description="Nome Ãºnico do asset por tenant"
    )
    
    # Tipo e valor
    tipo: TipoAssetEnum = Field(
        sa_column=Column(String(20)),
        description="Tipo de dado do asset"
    )
    
    value: str = Field(
        description="Valor do asset (armazenamento genÃ©rico como string)"
    )
    
    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="DescriÃ§Ã£o do asset"
    )
    
    # Escopo
    scope: ScopeAssetEnum = Field(
        default=ScopeAssetEnum.GLOBAL,
        sa_column=Column(String(20), index=True),
        description="Escopo de visibilidade (global/processo)"
    )
    
    scope_id: Optional[UUID] = Field(
        default=None,
        foreign_key="processo.id",
        index=True,
        description="ID do processo (se scope=processo)"
    )
    
    # Relacionamentos
    processo: Optional["Processo"] = Relationship(
        back_populates="assets",
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    
    @field_validator('scope_id')
    def validate_scope_id(cls, v, info):
        """Valida que scope_id Ã© obrigatÃ³rio quando scope=processo."""
        if info.data.get('scope') == ScopeAssetEnum.PROCESSO and not v:
            raise ValueError("scope_id Ã© obrigatÃ³rio quando scope='processo'")
        if info.data.get('scope') == ScopeAssetEnum.GLOBAL and v:
            raise ValueError("scope_id deve ser None quando scope='global'")
        return v
    
    def __repr__(self) -> str:
        return f"<Asset(id={self.id}, name={self.name}, tipo={self.tipo})>"


class Credencial(BaseModel, table=True):
    """
    Representa credenciais sensÃ­veis criptografadas.
    
    Armazena:
    - Diferentes tipos de autenticaÃ§Ã£o
    - Senha sempre criptografada (Fernet/AES-256)
    - Controle de expiraÃ§Ã£o e rotaÃ§Ã£o
    
    IMPORTANTE: encrypted_password NUNCA deve ser retornado via API.
    """
    
    __tablename__ = "credencial"
    
    # IdentificaÃ§Ã£o
    name: str = Field(
        max_length=100,
        index=True,
        description="Nome Ãºnico da credencial por tenant"
    )
    
    # Tipo
    tipo: TipoCredencialEnum = Field(
        sa_column=Column(String(20)),
        description="Tipo de credencial"
    )
    
    # Dados de autenticaÃ§Ã£o
    username: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Nome de usuÃ¡rio (se aplicÃ¡vel)"
    )
    
    encrypted_password: str = Field(
        description="Senha/token criptografado (NUNCA retornar via API)"
    )
    
    # Metadados por tipo
    extra_data: dict = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Campos adicionais específicos do tipo de credencial"
    )
    
    # Controle de expiraÃ§Ã£o
    expires_at: Optional[datetime] = Field(
        default=None,
        index=True,
        description="Data de expiraÃ§Ã£o da credencial"
    )
    
    last_rotated: Optional[datetime] = Field(
        default=None,
        description="Data da Ãºltima rotaÃ§Ã£o de senha"
    )
    
    rotation_days: Optional[int] = Field(
        default=None,
        description="Dias para aviso de rotaÃ§Ã£o (ex: 90)"
    )
    
    def __repr__(self) -> str:
        return f"<Credencial(id={self.id}, name={self.name}, tipo={self.tipo})>"


class Agendamento(BaseModel, table=True):
    """
    Representa um agendamento cron de processo.
    
    Gerencia:
    - ExpressÃ£o cron
    - Timezone
    - ParÃ¢metros de entrada fixos
    - PrÃ³xima execuÃ§Ã£o calculada
    """
    
    __tablename__ = "agendamento"
    
    # Foreign Keys
    processo_id: UUID = Field(
        foreign_key="processo.id",
        nullable=False,
        index=True,
        description="ID do processo a ser agendado"
    )
    
    # IdentificaÃ§Ã£o
    name: str = Field(
        max_length=100,
        description="Nome descritivo do agendamento"
    )
    
    # ConfiguraÃ§Ã£o cron
    cron_expression: str = Field(
        max_length=100,
        description="ExpressÃ£o cron (ex: '0 9 * * 1-5' = 9h segunda a sexta)"
    )
    
    timezone: str = Field(
        default="UTC",
        max_length=50,
        description="Timezone para o agendamento (ex: 'America/Sao_Paulo')"
    )
    
    # Status
    is_active: bool = Field(
        default=True,
        index=True,
        description="Agendamento ativo"
    )
    
    # ParÃ¢metros de entrada
    input_data: dict = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="ParÃ¢metros fixos para o processo"
    )
    
    # Controle de execuÃ§Ã£o
    last_run_at: Optional[datetime] = Field(
        default=None,
        description="Data/hora da Ãºltima execuÃ§Ã£o"
    )
    
    next_run_at: datetime = Field(
        index=True,
        description="PrÃ³xima execuÃ§Ã£o calculada (baseada no cron)"
    )
    
    # Relacionamentos
    processo: "Processo" = Relationship(
        back_populates="agendamentos",
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    
    @field_validator('cron_expression')
    def validate_cron_expression(cls, v):
        """
        Valida formato bÃ¡sico de expressÃ£o cron.
        
        Formato: minuto hora dia mÃªs dia_semana
        Ex: '0 9 * * 1-5' = 9h segunda a sexta
        """
        from croniter import croniter
        
        if not croniter.is_valid(v):
            raise ValueError(f"ExpressÃ£o cron invÃ¡lida: {v}")
        return v
    
    def __repr__(self) -> str:
        return f"<Agendamento(id={self.id}, name={self.name}, cron={self.cron_expression})>"


# ==================== INDEXES ====================

# Asset
Index('idx_asset_tenant_name', Asset.tenant_id, Asset.name, unique=True)
Index('idx_asset_tenant_scope', Asset.tenant_id, Asset.scope)

# Credencial
Index('idx_credencial_tenant_name', Credencial.tenant_id, Credencial.name, unique=True)
Index('idx_credencial_expires', Credencial.expires_at)

# Agendamento
Index('idx_agendamento_tenant_active_next',
      Agendamento.tenant_id,
      Agendamento.is_active,
      Agendamento.next_run_at.asc())
Index('idx_agendamento_processo', Agendamento.processo_id)