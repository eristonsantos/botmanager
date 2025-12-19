# backend/app/services/process_service.py

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
from uuid import UUID

from sqlalchemy import func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.core import Processo, VersaoProcesso

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Exceptions (tenta usar as do projeto; fallback para locais)
# -----------------------------------------------------------------------------
try:
    from app.core.exceptions import NotFoundError, ConflictError  # type: ignore
except Exception:  # pragma: no cover
    class NotFoundError(Exception):
        pass

    class ConflictError(Exception):
        pass


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _model_dump(obj: Any, *, exclude_unset: bool = True) -> Dict[str, Any]:
    """Suporta Pydantic v2 (model_dump) e fallback para dict."""
    if obj is None:
        return {}
    if hasattr(obj, "model_dump"):
        return obj.model_dump(exclude_unset=exclude_unset)
    if isinstance(obj, dict):
        return obj
    # fallback conservador
    return {}


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


# -----------------------------------------------------------------------------
# Service
# -----------------------------------------------------------------------------
class ProcessService:
    def __init__(self, session: AsyncSession):
        self.session = session

    # -------------------------------------------------------------------------
    # Core: processos
    # -------------------------------------------------------------------------
    async def _get_by_name(self, tenant_id: UUID, name: str) -> Optional[Processo]:
        stmt = (
            select(Processo)
            .where(Processo.tenant_id == tenant_id)
            .where(Processo.name == name)
            .where(Processo.deleted_at.is_(None))
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_process(self, tenant_id: UUID, processo_id: UUID) -> Processo:
        stmt = (
            select(Processo)
            .where(Processo.tenant_id == tenant_id)
            .where(Processo.id == processo_id)
            .where(Processo.deleted_at.is_(None))
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        if not obj:
            raise NotFoundError("Processo não encontrado.")
        return obj

    async def create_process(self, tenant_id: UUID, data: Any) -> Processo:
        payload = _model_dump(data)

        name = payload.get("name")
        if not name:
            raise ValueError("Campo obrigatório: name")

        existing = await self._get_by_name(tenant_id, name)
        if existing:
            raise ConflictError("Já existe um processo com este nome para este tenant.")

        processo = Processo(
            tenant_id=tenant_id,
            name=name,
            description=payload.get("description"),
            tipo=payload.get("tipo"),
            tags=payload.get("tags") or [],
            is_active=payload.get("is_active", True),
            extra_data=payload.get("extra_data") or {},
        )

        self.session.add(processo)
        await self.session.commit()
        await self.session.refresh(processo)

        logger.info("Created process %s for tenant %s", processo.id, tenant_id)
        return processo

    async def update_process(self, tenant_id: UUID, processo_id: UUID, data: Any) -> Processo:
        processo = await self.get_process(tenant_id, processo_id)
        payload = _model_dump(data)

        # rename com proteção de unicidade por tenant
        if "name" in payload and payload["name"] and payload["name"] != processo.name:
            existing = await self._get_by_name(tenant_id, payload["name"])
            if existing and existing.id != processo.id:
                raise ConflictError("Já existe um processo com este nome para este tenant.")
            processo.name = payload["name"]

        if "description" in payload:
            processo.description = payload["description"]

        if "tipo" in payload and payload["tipo"] is not None:
            processo.tipo = payload["tipo"]

        if "tags" in payload and payload["tags"] is not None:
            processo.tags = payload["tags"]

        if "is_active" in payload and payload["is_active"] is not None:
            processo.is_active = payload["is_active"]

        if "extra_data" in payload and payload["extra_data"] is not None:
            processo.extra_data = payload["extra_data"]

        self.session.add(processo)
        await self.session.commit()
        await self.session.refresh(processo)

        logger.info("Updated process %s for tenant %s", processo.id, tenant_id)
        return processo

    async def delete_process(self, tenant_id: UUID, processo_id: UUID) -> Processo:
        processo = await self.get_process(tenant_id, processo_id)
        processo.deleted_at = _now_utc()

        self.session.add(processo)
        await self.session.commit()
        await self.session.refresh(processo)

        logger.info("Soft-deleted process %s for tenant %s", processo.id, tenant_id)
        return processo

    # -------------------------------------------------------------------------
    # Listagem (otimizada) + filtros + paginação
    # -------------------------------------------------------------------------
    async def list_processes(
        self,
        tenant_id: UUID,
        *,
        tipo: Optional[str] = None,
        is_active: Optional[bool] = None,
        tags: Optional[Sequence[str]] = None,
        tag_match: str = "any",  # any|all
        search: Optional[str] = None,
        page: int = 1,
        size: int = 10,
        include_stats: bool = True,
    ) -> Tuple[List[Processo], int]:
        """
        Retorna (items, total). Se include_stats=True, calcula para os itens da página:
        - total_versions (count por processo)
        - active_version (obj VersaoProcesso por processo, quando existir)

        Isso evita N+1. Em vez de (N + 1) queries, vira:
        1) query página de processos
        2) query total count
        3) (opcional) query counts por processo_id (GROUP BY)
        4) (opcional) query active versions para os processo_id da página
        """
        page = max(page, 1)
        size = max(size, 1)

        stmt = (
            select(Processo)
            .where(Processo.tenant_id == tenant_id)
            .where(Processo.deleted_at.is_(None))
        )

        # filtros
        if tipo:
            stmt = stmt.where(Processo.tipo == tipo)

        if is_active is not None:
            stmt = stmt.where(Processo.is_active == is_active)

        if search:
            s = f"%{search.strip()}%"
            stmt = stmt.where(or_(Processo.name.ilike(s), Processo.description.ilike(s)))

        if tags:
            # garante lista (se alguém passou string por acidente)
            if isinstance(tags, str):
                tags = [tags]

            tags = [t for t in tags if t]  # limpa vazios

            if tags:
                tag_match = (tag_match or "any").lower()

                if tag_match == "all":
                    # ALL: todas as tags devem existir
                    for t in tags:
                        stmt = stmt.where(Processo.tags.op("?")(t))
                else:
                    # ANY: pelo menos uma tag
                    stmt = stmt.where(or_(*[Processo.tags.op("?")(t) for t in tags]))

        # total (sem paginação)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_res = await self.session.execute(count_stmt)
        total = int(total_res.scalar_one() or 0)

        # paginação
        page_stmt = (
            stmt.order_by(Processo.created_at.desc())  # type: ignore[attr-defined]
            .offset((page - 1) * size)
            .limit(size)
        )
        res = await self.session.execute(page_stmt)
        items = list(res.scalars().all())

        if include_stats and items:
            processo_ids = [p.id for p in items]

            # 1) counts por processo
            counts_map = await self.get_total_versions(
                processo_ids, tenant_id=tenant_id  # type: ignore[arg-type]
            )

            # 2) active version por processo
            active_map = await self.get_active_version(
                processo_ids, tenant_id=tenant_id  # type: ignore[arg-type]
            )

            # Anexa como atributos transitórios (útil para montar response sem N+1).
            # Se você preferir NÃO setar attrs no model, use os maps diretamente no router.
            for p in items:
                try:
                    object.__setattr__(p, "total_versions", counts_map.get(p.id, 0))
                    object.__setattr__(p, "active_version", active_map.get(p.id))
                except Exception:
                    # se por alguma razão o model bloquear setattr, apenas ignore
                    pass

        logger.info(
            "Listed %s processes for tenant %s (total: %s)",
            len(items),
            tenant_id,
            total,
        )
        return items, total

    # -------------------------------------------------------------------------
    # Versionamento
    # -------------------------------------------------------------------------
    async def create_version(self, tenant_id: UUID, processo_id: UUID, data: Any) -> VersaoProcesso:
        processo = await self.get_process(tenant_id, processo_id)
        payload = _model_dump(data)

        version = payload.get("version")
        package_path = payload.get("package_path")
        if not version:
            raise ValueError("Campo obrigatório: version")
        if not package_path:
            raise ValueError("Campo obrigatório: package_path")

        # impede duplicidade (tenant + processo + version)
        stmt_dup = (
            select(VersaoProcesso.id)
            .where(VersaoProcesso.tenant_id == tenant_id)
            .where(VersaoProcesso.processo_id == processo.id)
            .where(VersaoProcesso.version == version)
            .where(VersaoProcesso.deleted_at.is_(None))
            .limit(1)
        )
        dup_res = await self.session.execute(stmt_dup)
        if dup_res.scalar_one_or_none():
            raise ConflictError("Já existe esta versão para este processo.")

        versao = VersaoProcesso(
            tenant_id=tenant_id,
            processo_id=processo.id,
            version=version,
            package_path=package_path,
            release_notes=payload.get("release_notes"),
            config=payload.get("config") or {},
            is_active=bool(payload.get("is_active", False)),
        )

        self.session.add(versao)

        # regra prática: se é a primeira versão do processo, você pode ativar automaticamente
        # (mantive conservador: só ativa se o payload pedir is_active=True)
        if versao.is_active:
            await self._deactivate_other_versions(
                tenant_id=tenant_id,
                processo_id=processo.id,
                keep_version_id=None,
            )

        await self.session.commit()
        await self.session.refresh(versao)

        logger.info(
            "Created process version %s (%s) for process %s tenant %s",
            versao.id,
            versao.version,
            processo.id,
            tenant_id,
        )
        return versao

    async def list_versions(self, tenant_id: UUID, processo_id: UUID) -> List[VersaoProcesso]:
        processo = await self.get_process(tenant_id, processo_id)
        stmt = (
            select(VersaoProcesso)
            .where(VersaoProcesso.tenant_id == tenant_id)
            .where(VersaoProcesso.processo_id == processo.id)
            .where(VersaoProcesso.deleted_at.is_(None))
            .order_by(VersaoProcesso.created_at.desc())  # type: ignore[attr-defined]
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def activate_version(self, tenant_id: UUID, processo_id: UUID, versao_id: UUID) -> VersaoProcesso:
        processo = await self.get_process(tenant_id, processo_id)

        stmt = (
            select(VersaoProcesso)
            .where(VersaoProcesso.tenant_id == tenant_id)
            .where(VersaoProcesso.processo_id == processo.id)
            .where(VersaoProcesso.id == versao_id)
            .where(VersaoProcesso.deleted_at.is_(None))
        )
        res = await self.session.execute(stmt)
        versao = res.scalar_one_or_none()
        if not versao:
            raise NotFoundError("Versão não encontrada para este processo.")

        await self._deactivate_other_versions(
            tenant_id=tenant_id,
            processo_id=processo.id,
            keep_version_id=versao.id,
        )

        versao.is_active = True
        self.session.add(versao)
        await self.session.commit()
        await self.session.refresh(versao)

        logger.info("Activated version %s for process %s tenant %s", versao.id, processo.id, tenant_id)
        return versao

    async def _deactivate_other_versions(
        self,
        *,
        tenant_id: UUID,
        processo_id: UUID,
        keep_version_id: Optional[UUID],
    ) -> None:
        """
        Desativa todas as versões do processo (exceto keep_version_id quando informado).
        Mantém ORM para simplicidade; custo é baixo pois opera em poucas linhas.
        """
        stmt = (
            select(VersaoProcesso)
            .where(VersaoProcesso.tenant_id == tenant_id)
            .where(VersaoProcesso.processo_id == processo_id)
            .where(VersaoProcesso.deleted_at.is_(None))
        )
        if keep_version_id:
            stmt = stmt.where(VersaoProcesso.id != keep_version_id)

        res = await self.session.execute(stmt)
        versions = list(res.scalars().all())

        changed = 0
        for v in versions:
            if v.is_active:
                v.is_active = False
                self.session.add(v)
                changed += 1

        if changed:
            logger.debug("Deactivated %s versions for process %s", changed, processo_id)

    # -------------------------------------------------------------------------
    # Stats (otimizados) – suportam UUID ou lista de UUIDs
    # -------------------------------------------------------------------------
    async def get_total_versions(
        self,
        processo_id: Union[UUID, Sequence[UUID]],
        *,
        tenant_id: Optional[UUID] = None,
    ) -> Union[int, Dict[UUID, int]]:
        """
        - Se receber UUID: retorna int.
        - Se receber lista: retorna dict[processo_id] = count.
        """
        if isinstance(processo_id, (list, tuple, set)):
            ids = list(processo_id)
            if not ids:
                return {}

            stmt = (
                select(
                    VersaoProcesso.processo_id,
                    func.count(VersaoProcesso.id).label("total_versions"),
                )
                .where(VersaoProcesso.processo_id.in_(ids))
                .where(VersaoProcesso.deleted_at.is_(None))
                .group_by(VersaoProcesso.processo_id)
            )
            if tenant_id:
                stmt = stmt.where(VersaoProcesso.tenant_id == tenant_id)

            res = await self.session.execute(stmt)
            rows = res.all()
            out: Dict[UUID, int] = {pid: int(cnt) for pid, cnt in rows}
            # garante zero para os que não vieram
            for pid in ids:
                out.setdefault(pid, 0)
            return out

        # UUID único
        stmt = (
            select(func.count(VersaoProcesso.id))
            .where(VersaoProcesso.processo_id == processo_id)
            .where(VersaoProcesso.deleted_at.is_(None))
        )
        if tenant_id:
            stmt = stmt.where(VersaoProcesso.tenant_id == tenant_id)
        res = await self.session.execute(stmt)
        return int(res.scalar_one() or 0)

    async def get_active_version(
        self,
        processo_id: Union[UUID, Sequence[UUID]],
        *,
        tenant_id: Optional[UUID] = None,
    ) -> Union[Optional[VersaoProcesso], Dict[UUID, Optional[VersaoProcesso]]]:
        """
        - Se receber UUID: retorna VersaoProcesso | None.
        - Se receber lista: retorna dict[processo_id] = VersaoProcesso | None.

        Observação: pelo seu modelo, a regra é "apenas 1 ativa por processo".
        """
        if isinstance(processo_id, (list, tuple, set)):
            ids = list(processo_id)
            if not ids:
                return {}

            stmt = (
                select(VersaoProcesso)
                .where(VersaoProcesso.processo_id.in_(ids))
                .where(VersaoProcesso.is_active.is_(True))
                .where(VersaoProcesso.deleted_at.is_(None))
            )
            if tenant_id:
                stmt = stmt.where(VersaoProcesso.tenant_id == tenant_id)

            res = await self.session.execute(stmt)
            versions = list(res.scalars().all())

            out: Dict[UUID, Optional[VersaoProcesso]] = {pid: None for pid in ids}
            for v in versions:
                out[v.processo_id] = v

            return out

        # UUID único
        stmt = (
            select(VersaoProcesso)
            .where(VersaoProcesso.processo_id == processo_id)
            .where(VersaoProcesso.is_active.is_(True))
            .where(VersaoProcesso.deleted_at.is_(None))
            .limit(1)
        )
        if tenant_id:
            stmt = stmt.where(VersaoProcesso.tenant_id == tenant_id)

        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()
