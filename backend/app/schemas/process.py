# backend/app/schemas/process.py
"""
Schemas Pydantic para gestão de Processos RPA e Versões.

Define:
- ProcessBase: Campos base do processo
- ProcessCreate: Request de criação
- ProcessRead: Response de leitura
- ProcessUpdate: Request de atualização
- ProcessFilterParams: Filtros avançados
- VersaoBase: Campos base da versão
- VersaoCreate: Request de criação de versão
- VersaoRead: Response de leitura
- VersaoReadFull: Response com processo completo

Endpoints suportados (Fase 5A):
- GET    /processes                    (listagem paginada + filtros)
- GET    /processes/{id}               (detalhe com versao_ativa)
- POST   /processes                    (criar)
- PUT    /processes/{id}               (atualizar)
- DELETE /processes/{id}               (soft delete)
- GET    /processes/{id}/versions      (listar versões)
- POST   /processes/{id}/versions      (criar versão)
- PUT    /processes/{id}/versions/{vid}/activate (ativar versão)
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from enum import Enum
from fastapi import Query


from pydantic import Field, field_validator

from app.models.core import TipoProcessoEnum
from .common import BaseSchema, TenantMixin, TimestampMixin, PaginationParams


# ==================== PROCESS BASE SCHEMAS ====================

class TagMatchEnum(str, Enum):
    """Modo de match para filtro de tags"""
    ANY = "any"    # Tag1 OR Tag2 OR Tag3
    ALL = "all"    # Tag1 AND Tag2 AND Tag3


class ProcessBase(BaseSchema):
    """Campos base do processo (compartilhados entre Create/Update)"""
    
    name: str = Field(
        min_length=3,
        max_length=100,
        description="Nome único do processo por tenant",
        examples=["invoice_processing"]
    )
    
    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Descrição detalhada do processo"
    )
    
    tipo: TipoProcessoEnum = Field(
        description="Tipo de processo (attended/unattended/hybrid)",
        examples=["unattended"]
    )
    
    tags: List[str] = Field(
        default_factory=list,
        min_length=0,
        max_length=20,
        description="Tags para categorização (máx 20)",
        examples=[["financeiro", "mensal"]]
    )
    
    extra_data: dict = Field(
        default_factory=dict,
        description="Dados extras (JSON livre)"
    )
    
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        """Valida tags"""
        if len(v) > 20:
            raise ValueError("Máximo 20 tags permitidas")
        
        # Remove duplicatas, converte para lowercase
        unique_tags = list(set(tag.lower().strip() for tag in v if tag.strip()))
        return unique_tags


class ProcessCreate(ProcessBase):
    """Schema para criar novo processo"""
    pass


class ProcessUpdate(BaseSchema):
    """Schema para atualizar processo (todos campos opcionais)"""
    
    name: Optional[str] = Field(
        default=None,
        min_length=3,
        max_length=100
    )
    
    description: Optional[str] = Field(
        default=None,
        max_length=500
    )
    
    tipo: Optional[TipoProcessoEnum] = Field(default=None)
    
    tags: Optional[List[str]] = Field(default=None)
    
    is_active: Optional[bool] = Field(
        default=None,
        description="Ativar/desativar processo"
    )
    
    extra_data: Optional[dict] = Field(default=None)


class ProcessRead(TenantMixin, TimestampMixin):
    """Schema para retornar processo (response)"""
    
    id: UUID = Field(description="ID único do processo")
    name: str = Field(description="Nome do processo")
    description: Optional[str] = Field(description="Descrição")
    tipo: TipoProcessoEnum = Field(description="Tipo do processo")
    tags: List[str] = Field(description="Tags")
    is_active: bool = Field(description="Processo ativo")
    extra_data: dict = Field(description="Dados extras")
    
    # Campos computados (vindos do service)
    total_versions: int = Field(
        description="Total de versões deste processo"
    )
    
    active_version: Optional[str] = Field(
        default=None,
        description="Versão ativa (X.Y.Z)"
    )
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "tenant_id": "550e8400-e29b-41d4-a716-446655440001",
                "name": "invoice_processing",
                "description": "Processa faturas automaticamente",
                "tipo": "unattended",
                "tags": ["financeiro", "mensal"],
                "is_active": True,
                "extra_data": {"priority": "high"},
                "total_versions": 3,
                "active_version": "2.1.0",
                "created_at": "2024-12-01T10:00:00Z",
                "updated_at": "2024-12-09T10:00:00Z"
            }
        }
    }


# ==================== PROCESS FILTER SCHEMAS ====================

class ProcessFilterParams(PaginationParams):
    """
    Parâmetros de filtro para listagem de processos.
    
    Herda de PaginationParams (page, size, skip, limit).
    """
    
    tipo: Optional[TipoProcessoEnum] = Field(
        default=None,
        description="Filtrar por tipo"
    )
    
    tags: Optional[List[str]] = Query(
        default=None,
        description="Filtrar por tags (multi)"
    )

    tag_match: TagMatchEnum = Field(
        default=TagMatchEnum.ANY,
        description="Modo de match para tags (ANY=OU, ALL=E)"
    )
    
    is_active: Optional[bool] = Field(
        default=None,
        description="Filtrar apenas processos ativos/inativos"
    )
    
    search: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Busca por nome ou descrição (ILIKE)"
    )
    
    sort_by: str = Field(
        default="created_at",
        description="Campo para ordenação",
        pattern="^(name|created_at|updated_at|tipo)$"
    )
    
    sort_order: str = Field(
        default="desc",
        description="Ordem de ordenação",
        pattern="^(asc|desc)$"
    )
    
    @property
    def tags_list(self) -> List[str]:
        if not self.tags:
            return []
        return [t.strip().lower() for t in self.tags if t and t.strip()]


# ==================== VERSION BASE SCHEMAS ====================

class VersaoBase(BaseSchema):
    """Campos base da versão (compartilhados)"""
    
    version: str = Field(
        min_length=5,
        max_length=20,
        description="Versão semântica (X.Y.Z)",
        examples=["1.0.0"]
    )
    
    package_path: str = Field(
        min_length=1,
        max_length=500,
        description="Caminho/URL do pacote ou código",
        examples=["/packages/invoice_v1.0.0.zip", "s3://bucket/processes/v1.0.0"]
    )
    
    release_notes: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Notas de release desta versão"
    )
    
    config: dict = Field(
        default_factory=dict,
        description="Configurações específicas da versão (JSON)"
    )
    
    @field_validator('version')
    @classmethod
    def validate_semver(cls, v: str) -> str:
        """Valida semantic versioning (X.Y.Z)"""
        import re
        pattern = r'^\d+\.\d+\.\d+$'
        if not re.match(pattern, v):
            raise ValueError(
                "Versão deve ser semantic versioning (ex: 1.0.0)"
            )
        return v


class VersaoCreate(VersaoBase):
    """Schema para criar nova versão"""
    pass


class VersaoRead(TenantMixin, TimestampMixin):
    """Schema para retornar versão (response simplificado)"""
    
    id: UUID = Field(description="ID único da versão")
    processo_id: UUID = Field(description="ID do processo pai")
    version: str = Field(description="Versão (X.Y.Z)")
    package_path: str = Field(description="Caminho do pacote")
    is_active: bool = Field(description="Versão ativa?")
    release_notes: Optional[str] = Field(description="Notas de release")
    config: dict = Field(description="Configurações")
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "660f9400-e29b-41d4-a716-446655440000",
                "tenant_id": "550e8400-e29b-41d4-a716-446655440001",
                "processo_id": "550e8400-e29b-41d4-a716-446655440000",
                "version": "1.0.0",
                "package_path": "s3://bucket/processes/v1.0.0",
                "is_active": True,
                "release_notes": "Initial release",
                "config": {"timeout": 300},
                "created_at": "2024-12-01T10:00:00Z",
                "updated_at": "2024-12-01T10:00:00Z"
            }
        }
    }


class VersaoReadFull(VersaoRead):
    """Schema com processo completo (evita N+1 em queries)"""
    
    processo: ProcessRead = Field(
        description="Processo completo associado"
    )


# ==================== ACTIVATE VERSION ====================

class ActivateVersionRequest(BaseSchema):
    """Request para ativar uma versão"""
    
    # Body vazio - apenas a rota identifica qual versão ativar
    class Config:
        json_schema_extra = {
            "example": {}
        }


class ActivateVersionResponse(BaseSchema):
    """Response ao ativar versão"""
    
    processo_id: UUID = Field(description="ID do processo")
    version: str = Field(description="Versão ativada")
    is_active: bool = Field(default=True, description="Confirmação")
    message: str = Field(
        default="Versão ativada com sucesso"
    )


# ==================== PROCESS WITH ACTIVE VERSION ====================

class ProcessReadWithVersion(ProcessRead):
    """
    Schema ProcessRead + Versão ativa incluída.
    
    Usado em GET /processes/{id} para retornar processo
    com informações da versão ativa sem N+1.
    """
    
    active_version_data: Optional[VersaoRead] = Field(
        default=None,
        description="Dados completos da versão ativa"
    )