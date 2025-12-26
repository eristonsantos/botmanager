# backend/app/services/execution_service.py
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.exceptions import NotFoundError, ConflictError
from app.core.logging import get_logger
from app.models.core import (
    Execucao, 
    Processo, 
    Agente, 
    VersaoProcesso, 
    StatusExecucaoEnum, 
    StatusAgenteEnum,
    TriggerTypeEnum
)
from app.schemas.execution import ExecutionCreate, ExecutionUpdate

logger = get_logger(__name__)

class ExecutionService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def trigger_execution(
        self, 
        tenant_id: UUID, 
        processo_id: UUID, 
        trigger_type: TriggerTypeEnum,
        agente_id: Optional[UUID] = None,
        input_data: Optional[dict] = None
    ) -> Execucao:
        """
        Inicia o ciclo de vida de uma execução.
        Valida processo, versão ativa e disponibilidade do agente.
        """
        # 1. Validar Processo e buscar Versão Ativa
        stmt_processo = select(Processo).where(
            Processo.id == processo_id, 
            Processo.tenant_id == tenant_id,
            Processo.deleted_at == None
        )
        res_p = await self.session.execute(stmt_processo)
        processo = res_p.scalar_one_or_none()
        
        if not processo:
            raise NotFoundError(resource="Processo", identifier=processo_id)

        # Buscar versão ativa
        stmt_versao = select(VersaoProcesso).where(
            VersaoProcesso.processo_id == processo_id,
            VersaoProcesso.is_active == True
        )
        res_v = await self.session.execute(stmt_versao)
        versao = res_v.scalar_one_or_none()

        if not versao:
            raise ConflictError(f"O processo {processo.name} não possui uma versão ativa para execução.")

        # 2. Validar Agente (se fornecido)
        if agente_id:
            stmt_agente = select(Agente).where(
                Agente.id == agente_id, 
                Agente.tenant_id == tenant_id
            )
            res_a = await self.session.execute(stmt_agente)
            agente = res_a.scalar_one_or_none()

            if not agente:
                raise NotFoundError(resource="Agente", identifier=agente_id)
            
            if agente.status == StatusAgenteEnum.OFFLINE:
                logger.warning(f"Tentativa de execução no agente {agente.name} que está OFFLINE.")

        # 3. Criar o registro de Execução (Status inicial: QUEUED)
        execucao = Execucao(
            tenant_id=tenant_id,
            processo_id=processo_id,
            versao_id=versao.id,
            agente_id=agente_id,
            status=StatusExecucaoEnum.QUEUED,
            trigger_type=trigger_type,
            parameters=input_data or {}
        )

        self.session.add(execucao)
        await self.session.commit()
        await self.session.refresh(execucao)

        logger.info(f"Execução {execucao.id} criada via {trigger_type} para o processo {processo.name}")
        
        # TODO: Aqui enviaremos uma notificação via Redis Pub/Sub para o Agente
        
        return execucao

    async def update_status(
        self, 
        tenant_id: UUID, 
        execution_id: UUID, 
        status: StatusExecucaoEnum,
        error_message: Optional[str] = None
    ) -> Execucao:
        """Atualiza o status da execução e gerencia timestamps de início/fim."""
        stmt = select(Execucao).where(
            Execucao.id == execution_id, 
            Execucao.tenant_id == tenant_id
        )
        res = await self.session.execute(stmt)
        execucao = res.scalar_one_or_none()

        if not execucao:
            raise NotFoundError(resource="Execucao", identifier=execution_id)

        execucao.status = status
        now = datetime.now(timezone.utc)

        if status == StatusExecucaoEnum.RUNNING:
            execucao.start_time = now
        
        elif status in [StatusExecucaoEnum.COMPLETED, StatusExecucaoEnum.FAILED, StatusExecucaoEnum.CANCELLED]:
            execucao.end_time = now
            if error_message:
                execucao.error_details = {"message": error_message}

        await self.session.commit()
        await self.session.refresh(execucao)
        return execucao

    async def get_execution_history(
        self, 
        tenant_id: UUID, 
        processo_id: Optional[UUID] = None,
        limit: int = 20
    ) -> List[Execucao]:
        """Retorna as últimas execuções para o dashboard."""
        stmt = select(Execucao).where(Execucao.tenant_id == tenant_id)
        
        if processo_id:
            stmt = stmt.where(Execucao.processo_id == processo_id)
        
        stmt = stmt.order_by(Execucao.created_at.desc()).limit(limit)
        res = await self.session.execute(stmt)
        return res.scalars().all()