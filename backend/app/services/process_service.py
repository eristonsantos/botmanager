# backend/app/services/process_service.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Sequence
from uuid import UUID

from sqlalchemy import func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.exceptions import NotFoundError, ConflictError
from app.core.logging import get_logger
from app.models.core import Processo, VersaoProcesso
from app.schemas.process import ProcessCreate, ProcessUpdate, ProcessFilterParams, VersaoCreate

logger = get_logger(__name__)

class ProcessService:
    def __init__(self, session: AsyncSession):
        self.session = session

    # =========================================================================
    # PROCESSOS (CRUD)
    # =========================================================================

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

        processo = Processo(**data.model_dump(), tenant_id=tenant_id)
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

    # =========================================================================
    # VERSÕES E ATIVAÇÃO
    # =========================================================================

    async def activate_version(self, tenant_id: UUID, processo_id: UUID, versao_id: UUID) -> VersaoProcesso:
        """
        Ativa uma versão específica e desativa todas as outras do mesmo processo.
        Garante atomicidade na troca de versão.
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
        desativar_stmt = (
            select(VersaoProcesso)
            .where(VersaoProcesso.processo_id == processo_id)
            .where(VersaoProcesso.is_active == True)
        )
        ativas_res = await self.session.execute(desativar_stmt)
        for v in ativas_res.scalars().all():
            v.is_active = False

        # 3. Ativar a versão desejada
        versao_alvo.is_active = True
        
        await self.session.commit()
        await self.session.refresh(versao_alvo)
        return versao_alvo

    async def get_active_version(self, tenant_id: UUID, processo_id: UUID) -> Optional[VersaoProcesso]:
        """Retorna a versão atualmente ativa de um processo."""
        stmt = select(VersaoProcesso).where(
            VersaoProcesso.processo_id == processo_id,
            VersaoProcesso.tenant_id == tenant_id,
            VersaoProcesso.is_active == True,
            VersaoProcesso.deleted_at == None
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()