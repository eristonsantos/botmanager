# backend/app/api/v1/processes.py
"""
Endpoints REST para Processos RPA e Versões.

Suporta:
- GET    /processes                    (listagem paginada + filtros)
- GET    /processes/{id}               (detalhe com versao_ativa)
- POST   /processes                    (criar)
- PUT    /processes/{id}               (atualizar)
- DELETE /processes/{id}               (soft delete)
- GET    /processes/{id}/versions      (listar versões)
- POST   /processes/{id}/versions      (criar versão)
- PUT    /processes/{id}/versions/{vid}/activate (ativar versão)

Padrão:
- Dependency injection de tenant_id (do JWT)
- Dependency injection de session (BD)
- Validação automática com Pydantic
- Error handling centralizado
"""

from uuid import UUID
from typing import List, Optional, Sequence

from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import get_current_tenant_id
from app.core.logging import get_logger
from app.schemas.process import (
    ProcessCreate,
    ProcessRead,
    ProcessUpdate,
    ProcessFilterParams,
    ProcessReadWithVersion,
    VersaoCreate,
    VersaoRead,
    ActivateVersionResponse,
)
from app.schemas.common import PaginatedResponse, MessageResponse
from app.services.process_service import ProcessService

logger = get_logger(__name__)

router = APIRouter(prefix="/processes", tags=["Processos"])


def _safe_list(v):
    if not v:
        return []
    if isinstance(v, str):
        return [v] if v.strip() else []
    return [x for x in v if x]


# ============================================================================
# PROCESSOS: LIST
# ============================================================================

@router.get(
    "",
    response_model=PaginatedResponse[ProcessRead],
    status_code=status.HTTP_200_OK,
    summary="Listar Processos",
    description="Lista processos do tenant com paginação e filtros avançados"
)
async def list_processes(
    filters: ProcessFilterParams = Depends(),
    tenant_id: UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session)
) -> PaginatedResponse[ProcessRead]:
    """
    Lista processos com suporte a:
    - Filtro por tipo (attended/unattended/hybrid)
    - Filtro por tags (ANY/ALL logic)
    - Busca textual (nome + descrição)
    - Paginação
    - Ordenação
    """
    service = ProcessService(session)

    # Desempacota filtros (evita passar objeto direto, pois o service espera kwargs)
    # Ajuste os nomes conforme seu ProcessFilterParams.
    tipo = getattr(filters, "tipo", None)
    is_active = getattr(filters, "is_active", None)
    tags = filters.tags_list
    tag_match = getattr(filters, "tag_match", "any") or "any"
    search = getattr(filters, "search", None)
    page = int(getattr(filters, "page", 1) or 1)
    size = int(getattr(filters, "size", 10) or 10)

    # 1) lista página (SEM stats)
    processes, total = await service.list_processes(
        tenant_id,
        tipo=tipo,
        is_active=is_active,
        tags=tags or None,
        tag_match=tag_match,
        search=search,
        page=page,
        size=size,
        include_stats=False,
    )

    # 2) stats em lote (evita N+1)
    items: List[ProcessRead] = []
    if processes:
        ids = [p.id for p in processes]

        total_versions_map = await service.get_total_versions(ids, tenant_id=tenant_id)
        active_versions_map = await service.get_active_version(ids, tenant_id=tenant_id)

        for p in processes:
            total_versions = 0
            if isinstance(total_versions_map, dict):
                total_versions = int(total_versions_map.get(p.id, 0))

            active_version_obj = None
            if isinstance(active_versions_map, dict):
                active_version_obj = active_versions_map.get(p.id)

            items.append(
                ProcessRead(
                    **p.__dict__,
                    total_versions=total_versions,
                    active_version=active_version_obj.version if active_version_obj else None,
                )
            )

    logger.info(f"Listed {len(items)} processes for tenant {tenant_id}")

    return PaginatedResponse.create(items, total, filters)


# ============================================================================
# PROCESSOS: GET (DETAIL)
# ============================================================================

@router.get(
    "/{processo_id}",
    response_model=ProcessReadWithVersion,
    status_code=status.HTTP_200_OK,
    summary="Obter Processo",
    description="Retorna detalhe do processo com versão ativa"
)
async def get_process(
    processo_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session)
) -> ProcessReadWithVersion:
    """
    Obtém processo específico com:
    - Dados completos do processo
    - Total de versões
    - Versão ativa (se houver)
    """
    service = ProcessService(session)

    processo = await service.get_process(tenant_id, processo_id)

    total_versions = await service.get_total_versions(processo_id, tenant_id=tenant_id)
    active_version = await service.get_active_version(processo_id, tenant_id=tenant_id)

    logger.info(f"Retrieved process {processo_id}")

    return ProcessReadWithVersion(
        **processo.__dict__,
        total_versions=int(total_versions) if isinstance(total_versions, int) else 0,
        active_version=active_version.version if active_version else None,
        active_version_data=VersaoRead.from_orm(active_version) if active_version else None,
    )


# ============================================================================
# PROCESSOS: CREATE
# ============================================================================

@router.post(
    "",
    response_model=ProcessRead,
    status_code=status.HTTP_201_CREATED,
    summary="Criar Processo",
    description="Cria novo processo"
)
async def create_process(
    data: ProcessCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session)
) -> ProcessRead:
    """Cria novo processo no tenant"""
    service = ProcessService(session)

    processo = await service.create_process(tenant_id, data)

    logger.info(f"Created process {processo.id}")

    return ProcessRead(
        **processo.__dict__,
        total_versions=0,
        active_version=None,
    )


# ============================================================================
# PROCESSOS: UPDATE
# ============================================================================

@router.put(
    "/{processo_id}",
    response_model=ProcessRead,
    status_code=status.HTTP_200_OK,
    summary="Atualizar Processo",
    description="Atualiza processo existente"
)
async def update_process(
    processo_id: UUID,
    data: ProcessUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session)
) -> ProcessRead:
    """Atualiza processo específico"""
    service = ProcessService(session)

    processo = await service.update_process(tenant_id, processo_id, data)

    total_versions = await service.get_total_versions(processo_id, tenant_id=tenant_id)
    active_version = await service.get_active_version(processo_id, tenant_id=tenant_id)

    logger.info(f"Updated process {processo_id}")

    return ProcessRead(
        **processo.__dict__,
        total_versions=int(total_versions) if isinstance(total_versions, int) else 0,
        active_version=active_version.version if active_version else None,
    )


# ============================================================================
# PROCESSOS: DELETE
# ============================================================================

@router.delete(
    "/{processo_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Deletar Processo",
    description="Soft delete de processo"
)
async def delete_process(
    processo_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session)
) -> MessageResponse:
    """Soft delete (versões são preservadas para auditoria)"""
    service = ProcessService(session)

    await service.delete_process(tenant_id, processo_id)

    logger.info(f"Deleted process {processo_id}")

    return MessageResponse(
        message=f"Processo {processo_id} deletado com sucesso",
        status="success",
    )


# ============================================================================
# VERSÕES: LIST
# ============================================================================

@router.get(
    "/{processo_id}/versions",
    response_model=PaginatedResponse[VersaoRead],
    status_code=status.HTTP_200_OK,
    summary="Listar Versões",
    description="Lista todas as versões de um processo"
)
async def list_versions(
    processo_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    tenant_id: UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session)
) -> PaginatedResponse[VersaoRead]:
    """
    Lista versões de um processo.

    Inclui todas as versões (ativas e inativas) para histórico completo.
    """
    service = ProcessService(session)

    # valida que processo existe e pertence ao tenant
    await service.get_process(tenant_id, processo_id)

    versoes = await service.list_versions(tenant_id, processo_id)

    items = [VersaoRead.from_orm(v) for v in versoes]
    total = len(items)

    skip = (page - 1) * size
    items_page = items[skip: skip + size]

    logger.info(f"Listed {len(items_page)} versions for process {processo_id}")

    return PaginatedResponse(
        items=items_page,
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


# ============================================================================
# VERSÕES: CREATE
# ============================================================================

@router.post(
    "/{processo_id}/versions",
    response_model=VersaoRead,
    status_code=status.HTTP_201_CREATED,
    summary="Criar Versão",
    description="Cria nova versão de um processo"
)
async def create_version(
    processo_id: UUID,
    data: VersaoCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session)
) -> VersaoRead:
    """
    Cria nova versão.

    - Nova versão começa como INATIVA (a menos que o service esteja configurado para ativar ao criar)
    - Use endpoint /activate para ativar
    """
    service = ProcessService(session)

    versao = await service.create_version(tenant_id, processo_id, data)

    logger.info(f"Created version {versao.version} for process {processo_id}")

    return VersaoRead.from_orm(versao)


# ============================================================================
# VERSÕES: ACTIVATE
# ============================================================================

@router.put(
    "/{processo_id}/versions/{versao_id}/activate",
    response_model=ActivateVersionResponse,
    status_code=status.HTTP_200_OK,
    summary="Ativar Versão",
    description="Ativa uma versão (desativa a anterior)"
)
async def activate_version(
    processo_id: UUID,
    versao_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session)
) -> ActivateVersionResponse:
    """
    Ativa versão específica.

    ⭐ Transação atômica:
    1. Desativa versão anterior (se houver)
    2. Ativa nova versão
    3. Garante que apenas 1 versão fica ativa
    """
    service = ProcessService(session)

    versao = await service.activate_version(tenant_id, processo_id, versao_id)

    logger.info(f"Activated version {versao.version} for process {processo_id}")

    return ActivateVersionResponse(
        processo_id=processo_id,
        version=versao.version,
        is_active=True,
        message=f"Versão {versao.version} ativada com sucesso",
    )


# ============================================================================
# EXPORT
# ============================================================================

__all__ = ["router"]
