# backend/app/models/__init__.py
"""
Módulo de modelos do Orquestrador RPA.

Exporta todos os modelos SQLModel para facilitar imports.

Exemplo de uso:
    from app.models import Processo, Execucao, Agente
    
Estrutura:
    - base: Classes base e mixins
    - tenant: Multi-tenancy e autenticação
    - core: Agentes, Processos, Versões, Execuções
    - workload: Filas e Exceções
    - governance: Assets, Credenciais, Agendamentos
    - monitoring: Auditoria e Logs
"""

# Base
from .base import BaseModel, SoftDeleteMixin

# Tenant e Autenticação
from .tenant import Tenant, User

# Core (modelos principais)
from .core import (
    Agente,
    Processo,
    VersaoProcesso,
    Execucao,
    # Enums
    StatusAgenteEnum,
    TipoProcessoEnum,
    StatusExecucaoEnum,
    TriggerTypeEnum
)

# Workload (filas e exceções)
from .workload import (
    ItemFila,
    Excecao,
    # Enums
    # PriorityEnum,
    StatusItemFilaEnum,
    TipoExcecaoEnum,
    SeverityEnum
)

# Governance (segurança e governança)
from .governance import (
    Asset,
    Credencial,
    Agendamento,
    # Enums
    TipoAssetEnum,
    ScopeAssetEnum,
    TipoCredencialEnum
)

# Monitoring (auditoria e logs)
from .monitoring import (
    AuditoriaEvento,
    LogExecucao,
    LogMetadata,
    # Enums
    ActionEnum,
    LogLevelEnum,
    TipoMetadataEnum
)


# Lista de exportação explícita
__all__ = [
    # Base
    "BaseModel",
    "SoftDeleteMixin",
    
    # Tenant
    "Tenant",
    "User",
    
    # Core
    "Agente",
    "Processo",
    "VersaoProcesso",
    "Execucao",
    "StatusAgenteEnum",
    "TipoProcessoEnum",
    "StatusExecucaoEnum",
    "TriggerTypeEnum",
    
    # Workload
    "ItemFila",
    "Excecao",
    "PriorityEnum",
    "StatusItemFilaEnum",
    "TipoExcecaoEnum",
    "SeverityEnum",
    
    # Governance
    "Asset",
    "Credencial",
    "Agendamento",
    "TipoAssetEnum",
    "ScopeAssetEnum",
    "TipoCredencialEnum",
    
    # Monitoring
    "AuditoriaEvento",
    "LogExecucao",
    "LogMetadata",
    "ActionEnum",
    "LogLevelEnum",
    "TipoMetadataEnum",
]


# Metadados do módulo
__version__ = "1.0.0"
__author__ = "Orquestrador RPA Team"