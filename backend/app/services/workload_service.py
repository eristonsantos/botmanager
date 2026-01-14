# backend/app/services/workload_service.py
from datetime import datetime, timedelta
from uuid import UUID
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, col, or_

from app.models.workload import ItemFila, StatusItemFilaEnum, Excecao, TipoExcecaoEnum
from app.schemas.workload import ItemFilaCreate, ExcecaoCreate
from app.core.exceptions import NotFoundError

class WorkloadService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_item(self, tenant_id: UUID, data: ItemFilaCreate) -> ItemFila:
        """Cria um novo item na fila."""
        item = ItemFila(
            tenant_id=tenant_id,
            queue_name=data.queue_name,
            reference=data.reference,
            priority=data.priority,
            payload=data.payload,
            max_retries=data.max_retries,
            status=StatusItemFilaEnum.PENDING
        )
        self.session.add(item)
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def get_next_item(
        self, 
        tenant_id: UUID, 
        queue_name: str, 
        agent_id: UUID
    ) -> Optional[ItemFila]:
        """
        Algoritmo de "Fetch & Lock":
        1. Busca item pendente com maior prioridade e mais antigo.
        2. Marca como RUNNING e define o locked_by (Robô).
        """
        # 1. Query para encontrar o candidato
        stmt = select(ItemFila).where(
            ItemFila.tenant_id == tenant_id,
            ItemFila.queue_name == queue_name,
            ItemFila.status == StatusItemFilaEnum.PENDING,
            ItemFila.locked_by.is_(None)
        ).order_by(
            ItemFila.priority.desc(), # Prioridade Alta primeiro
            ItemFila.created_at.asc() # FIFO (First In, First Out)
        ).limit(1).with_for_update(skip_locked=True) # Lock no banco para evitar race condition

        result = await self.session.execute(stmt)
        item = result.scalar_one_or_none()

        if item:
            # 2. Lock
            item.status = StatusItemFilaEnum.RUNNING
            item.locked_by = agent_id
            item.locked_at = datetime.utcnow()
            item.retry_count += 1
            
            self.session.add(item)
            await self.session.commit()
            await self.session.refresh(item)
            
        return item

    async def complete_item(self, tenant_id: UUID, item_id: UUID):
        stmt = select(ItemFila).where(ItemFila.id == item_id, ItemFila.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        item = result.scalar_one_or_none()
        
        if item:
            item.status = StatusItemFilaEnum.COMPLETED
            item.completed_at = datetime.utcnow()
            item.locked_by = None # Libera lock (opcional, mas bom pra histórico)
            self.session.add(item)
            await self.session.commit()

    async def fail_item(self, tenant_id: UUID, item_id: UUID, erro: ExcecaoCreate) -> str:
        stmt = select(ItemFila).where(ItemFila.id == item_id, ItemFila.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        item = result.scalar_one_or_none()
        
        status_final = StatusItemFilaEnum.FAILED
        
        if item:
            # Lógica de Retry
            if erro.tipo == TipoExcecaoEnum.SYSTEM and item.retry_count <= item.max_retries:
                status_final = StatusItemFilaEnum.RETRY
                # Volta para pendente para outro robô pegar
                item.status = StatusItemFilaEnum.PENDING
                item.locked_by = None
                item.last_error = f"Retry {item.retry_count}: {erro.message}"
            else:
                item.status = StatusItemFilaEnum.FAILED
                item.completed_at = datetime.utcnow() # Falhou, mas terminou processamento
                item.last_error = erro.message

            self.session.add(item)
            
            # Registrar Exceção na tabela separada
            nova_excecao = Excecao(
                tenant_id=tenant_id,
                item_fila_id=item.id,
                **erro.model_dump()
            )
            self.session.add(nova_excecao)
            
            await self.session.commit()
            
        return status_final