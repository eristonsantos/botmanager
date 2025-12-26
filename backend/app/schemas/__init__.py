# backend/app/schemas/__init__.py
"""
Schemas package - Pydantic schemas for API request/response.
"""

from .common import (
    BaseSchema,
    TenantMixin,
    TimestampMixin,
    PaginationParams,
    PaginatedResponse,
    MessageResponse,
    ErrorResponse,
)

from .auth import (
    UserCreate,
    UserRead,
    UserUpdate,
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    TenantRead,
)

from .agent import (
    AgentBase,
    AgentCreate,
    AgentRead,
    AgentUpdate,
    AgentFilterParams,
    HeartbeatRequest,
    HeartbeatResponse,
)

from .workload import (
    ItemFilaCreate,
    ItemFilaRead,
    ExcecaoCreate,
    ExcecaoRead,
    WorkloadActionResponse
)

__all__ = [
    # Common
    "BaseSchema",
    "TenantMixin",
    "TimestampMixin",
    "PaginationParams",
    "PaginatedResponse",
    "MessageResponse",
    "ErrorResponse",
    
    # Auth
    "UserCreate",
    "UserRead",
    "UserUpdate",
    "LoginRequest",
    "TokenResponse",
    "RefreshTokenRequest",
    "TenantRead",
    
    # Agent
    "AgentBase",
    "AgentCreate",
    "AgentRead",
    "AgentUpdate",
    "AgentFilterParams",
    "HeartbeatRequest",
    "HeartbeatResponse",

    # Workload (ADICIONADO AQUI)
    "ItemFilaCreate",
    "ItemFilaRead",
    "ExcecaoCreate",
    "ExcecaoRead",
    "WorkloadActionResponse",
]