# backend/app/services/process_service.py
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union, Any
from uuid import UUID

from sqlalchemy import func, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, col

from app.core.exceptions import NotFoundError, ConflictError
from app.core.logging import get_logger
from app.models.core import Processo, VersaoProcesso
from app.schemas.process import ProcessCreate, ProcessUpdate, VersaoCreate

logger = get_logger(__name__)

class ProcessService:
    def __init__(self, session: AsyncSession):
        self.session = session

    # =========================================================================
    # PROCESSOS (CRUD)
    # =========================================================================

    async def list_processes(
        self,
        tenant_id: UUID,
        tipo: Optional[str] = None,
        is_active: Optional[bool] = None,
        tags: Optional[List[str]] = None,
        tag_match: str = "any",
        search: Optional[str] = None,
        page: int = 1,
        size: int = 10,
        include_stats: bool = False
    ) -> Tuple[List[Processo], int]:
        """
        Lista processos com filtros avançados e paginação.
        """
        # 1. Query Base
        query = select(Processo).where(
            Processo.tenant_id == tenant_id,
            Processo.deleted_at == None
        )

        # 2. Filtros
        if tipo:
            query = query.where(Processo.tipo == tipo)
        
        if is_active is not None:
            query = query.where(Processo.is_active == is_active)

        if search:
            # Busca case-insensitive no nome ou descrição
            term = f"%{search}%"
            query = query.where(
                or_(
                    col(Processo.name).ilike(term),
                    col(Processo.description).ilike(term)
                )
            )

        if tags and len(tags) > 0:
            # Lógica simples para JSONB: Filtra se contiver as tags
            # Nota: Para produção pesada, usar operadores @> do Postgres é melhor
            conditions = [col(Processo.tags).contains([t]) for t in tags]
            if tag_match == "all":
                for cond in conditions:
                    query = query.where(cond)
            else: # any
                query = query.where(or_(*conditions))

        # 3. Contagem Total (para paginação)
        # Truque eficiente para contar sem trazer os dados
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.session.execute(count_query)).scalar_one()

        # 4. Ordenação e Paginação
        query = query.order_by(desc(Processo.created_at))
        query = query.offset((page - 1) * size).limit(size)

        # 5. Executar
        result = await self.session.execute(query)
        items = result.scalars().all()

        return items, total

    async def create_process(self, tenant_id: UUID, data: ProcessCreate) -> Processo:
        # Verificar duplicidade de nome no mesmo tenant
        stmt = select(Processo).where(
            Processo.tenant_id == tenant_id,
            Processo.name == data.name,
            Processo.deleted_at == None
        )
        existing = await self.session.execute(stmt)
        if existing.scalar_one_or_none():
            raise ConflictError(f"Já existe um processo com o nome '{data.name}'")

        # Converte tags para list se não for
        processo_dict = data.model_dump()
        
        processo = Processo(**processo_dict, tenant_id=tenant_id)
        self.session.add(processo)
        await self.session.commit()
        await self.session.refresh(processo)
        return processo

    async def get_process(self, tenant_id: UUID, processo_id: UUID) -> Processo:
        stmt = select(Processo).where(
            Processo.id == processo_id,
            Processo.tenant_id == tenant_id,
            Processo.deleted_at == None
        )
        result = await self.session.execute(stmt)
        processo = result.scalar_one_or_none()
        
        if not processo:
            raise NotFoundError(resource="Processo", identifier=processo_id)
        return processo

    async def update_process(self, tenant_id: UUID, processo_id: UUID, data: ProcessUpdate) -> Processo:
        processo = await self.get_process(tenant_id, processo_id)
        
        update_data = data.model_dump(exclude_unset=True)
        
        for key, value in update_data.items():
            setattr(processo, key, value)
            
        self.session.add(processo)
        await self.session.commit()
        await self.session.refresh(processo)
        return processo

    async def delete_process(self, tenant_id: UUID, processo_id: UUID):
        processo = await self.get_process(tenant_id, processo_id)
        
        # Soft Delete
        processo.deleted_at = datetime.utcnow()
        processo.is_active = False # Desativa também
        
        self.session.add(processo)
        await self.session.commit()

    # =========================================================================
    # VERSÕES
    # =========================================================================

    async def list_versions(self, tenant_id: UUID, processo_id: UUID) -> List[VersaoProcesso]:
        query = select(VersaoProcesso).where(
            VersaoProcesso.processo_id == processo_id,
            VersaoProcesso.tenant_id == tenant_id,
            VersaoProcesso.deleted_at == None
        ).order_by(desc(VersaoProcesso.created_at))
        
        result = await self.session.execute(query)
        return result.scalars().all()

    async def create_version(self, tenant_id: UUID, processo_id: UUID, data: VersaoCreate) -> VersaoProcesso:
        # Verifica se o processo existe
        await self.get_process(tenant_id, processo_id)

        # Verifica se versão já existe
        stmt = select(VersaoProcesso).where(
            VersaoProcesso.processo_id == processo_id,
            VersaoProcesso.version == data.version,
            VersaoProcesso.deleted_at == None
        )
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing:
            raise ConflictError(f"Versão {data.version} já existe para este processo.")

        versao = VersaoProcesso(
            **data.model_dump(), 
            processo_id=processo_id, 
            tenant_id=tenant_id,
            is_active=False # Nasce inativa por padrão
        )
        
        self.session.add(versao)
        await self.session.commit()
        await self.session.refresh(versao)
        return versao

    async def activate_version(self, tenant_id: UUID, processo_id: UUID, versao_id: UUID) -> VersaoProcesso:
        """
        Ativa uma versão específica e desativa todas as outras do mesmo processo.
        """
        # 1. Verificar se a versão existe e pertence ao processo/tenant
        stmt = select(VersaoProcesso).where(
            VersaoProcesso.id == versao_id,
            VersaoProcesso.processo_id == processo_id,
            VersaoProcesso.tenant_id == tenant_id
        )
        res = await self.session.execute(stmt)
        versao_alvo = res.scalar_one_or_none()

        if not versao_alvo:
            raise NotFoundError(resource="VersaoProcesso", identifier=versao_id)

        # 2. Desativar todas as versões deste processo
        desativar_stmt = select(VersaoProcesso).where(
            VersaoProcesso.processo_id == processo_id,
            VersaoProcesso.is_active == True
        )
        ativas_res = await self.session.execute(desativar_stmt)
        for v in ativas_res.scalars().all():
            v.is_active = False
            self.session.add(v)

        # 3. Ativar a versão desejada
        versao_alvo.is_active = True
        self.session.add(versao_alvo)
        
        await self.session.commit()
        await self.session.refresh(versao_alvo)
        return versao_alvo

    # =========================================================================
    # ESTATÍSTICAS EM LOTE (Evita N+1 na listagem)
    # =========================================================================

    async def get_active_version(self, processo_ids: Union[UUID, List[UUID]], tenant_id: UUID) -> Union[Optional[VersaoProcesso], Dict[UUID, VersaoProcesso]]:
        """
        Retorna a versão ativa. Se receber uma lista de IDs, retorna um dicionário {processo_id: versao}.
        """
        is_single = isinstance(processo_ids, UUID)
        ids = [processo_ids] if is_single else processo_ids

        if not ids:
            return {} if not is_single else None

        stmt = select(VersaoProcesso).where(
            VersaoProcesso.processo_id.in_(ids),
            VersaoProcesso.tenant_id == tenant_id,
            VersaoProcesso.is_active == True,
            VersaoProcesso.deleted_at == None
        )
        result = await self.session.execute(stmt)
        versoes = result.scalars().all()

        if is_single:
            return versoes[0] if versoes else None
        
        return {v.processo_id: v for v in versoes}

    async def get_total_versions(self, processo_ids: Union[UUID, List[UUID]], tenant_id: UUID) -> Union[int, Dict[UUID, int]]:
        """
        Conta quantas versões existem. Se lista, retorna dict {processo_id: count}.
        """
        is_single = isinstance(processo_ids, UUID)
        ids = [processo_ids] if is_single else processo_ids

        if not ids:
            return {} if not is_single else 0

        # Query agrupada
        stmt = select(VersaoProcesso.processo_id, func.count(VersaoProcesso.id))\
            .where(
                VersaoProcesso.processo_id.in_(ids),
                VersaoProcesso.tenant_id == tenant_id,
                VersaoProcesso.deleted_at == None
            )\
            .group_by(VersaoProcesso.processo_id)
        
        result = await self.session.execute(stmt)
        rows = result.all() # [(uuid, count), ...]
        
        counts = {row[0]: row[1] for row in rows}

        if is_single:
            return counts.get(processo_ids, 0)
        
        return counts