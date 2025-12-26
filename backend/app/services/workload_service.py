from datetime import datetime, timezone, timedelta
from typing import Optional, List, Tuple
from uuid import UUID

from sqlalchemy import select, update, and_, or_  # Adicionado or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.workload import ItemFila, StatusItemFilaEnum, Excecao, TipoExcecaoEnum
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger

logger = get_logger(__name__)

class WorkloadService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_next_item(
        self, 
        tenant_id: UUID, 
        queue_name: str, 
        agent_id: UUID,
        lock_duration_minutes: int = 5
    ) -> Optional[ItemFila]:
        """
        Busca o próximo item disponível com prioridade e aplica lock atômico.
        """
        now = datetime.now(timezone.utc)
        
        # Query otimizada para concorrência
        stmt = (
            select(ItemFila.id)
            .where(
                ItemFila.tenant_id == tenant_id,
                ItemFila.queue_name == queue_name,
                ItemFila.status.in_([StatusItemFilaEnum.PENDING, StatusItemFilaEnum.RETRY]),
                or_(ItemFila.deferred_until == None, ItemFila.deferred_until <= now),
                or_(ItemFila.locked_until == None, ItemFila.locked_until <= now)
            )
            .order_by(ItemFila.priority.desc(), ItemFila.created_at.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )

        result = await self.session.execute(stmt)
        item_id = result.scalar_one_or_none()

        if not item_id:
            return None

        lock_expiration = now + timedelta(minutes=lock_duration_minutes)
        
        # Atualização atômica
        update_stmt = (
            update(ItemFila)
            .where(ItemFila.id == item_id)
            .values(
                status=StatusItemFilaEnum.PROCESSING,
                locked_by=agent_id,
                locked_until=lock_expiration,
                updated_at=now
            )
            .returning(ItemFila)
        )
        
        updated_result = await self.session.execute(update_stmt)
        item = updated_result.scalar_one()
        
        await self.session.commit()
        return item

    async def fail_item(
        self,
        tenant_id: UUID,
        item_id: UUID,
        exception_type: TipoExcecaoEnum,
        message: str,
        stack_trace: Optional[str] = None,
        execution_id: Optional[UUID] = None
    ) -> ItemFila:
        """
        Registra falha e gerencia retentativas.
        """
        item = await self.session.get(ItemFila, item_id)
        if not item or item.tenant_id != tenant_id:
            raise NotFoundError("ItemFila", item_id)

        now = datetime.now(timezone.utc)
        
        # Criar registro de erro para o dashboard
        excecao = Excecao(
            tenant_id=tenant_id,
            item_fila_id=item.id,
            execucao_id=execution_id or item.execucao_id,
            tipo=exception_type,
            message=message[:500], # Trunkate para segurança
            stack_trace=stack_trace,
            severity="high" if exception_type == TipoExcecaoEnum.SYSTEM else "medium"
        )
        self.session.add(excecao)

        # Lógica de Retry
        if exception_type == TipoExcecaoEnum.SYSTEM and item.retry_count < item.max_retries:
            item.status = StatusItemFilaEnum.RETRY
            item.retry_count += 1
            # Backoff: 10, 20, 30 minutos...
            item.deferred_until = now + timedelta(minutes=item.retry_count * 10)
        else:
            item.status = StatusItemFilaEnum.FAILED

        item.locked_until = None
        item.locked_by = None
        
        await self.session.commit()
        await self.session.refresh(item)
        return item