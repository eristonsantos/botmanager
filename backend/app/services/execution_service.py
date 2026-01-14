# backend/app/services/execution_service.py
from uuid import UUID
from datetime import datetime
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, desc, func

from app.models.core import Execucao, Processo, VersaoProcesso, StatusExecucaoEnum, TriggerTypeEnum
from app.models.workload import ItemFila, StatusItemFilaEnum #, PriorityEnum
from app.schemas.execution import ExecutionCreate, ExecutionFilterParams, ExecutionSummary, ExecutionRead, ExecutionUpdate
from app.core.exceptions import NotFoundError, BusinessError

class ExecutionService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def trigger_manual_execution(self, tenant_id: UUID, data: ExecutionCreate) -> Execucao:
        """
        Cria uma Execução E um Item na Fila de trabalho correspondente.
        """
        # 1. Validar se o Processo existe e pertence ao Tenant
        stmt = select(Processo).where(
            Processo.id == data.processo_id,
            Processo.tenant_id == tenant_id
        )
        processo = (await self.session.execute(stmt)).scalar_one_or_none()
        
        if not processo:
            raise NotFoundError(resource="Processo", identifier=data.processo_id)

        if not processo.is_active:
            raise BusinessError("Este processo está inativo e não pode ser executado.")

        # 2. Buscar a Versão Ativa (necessária para execução)
        stmt_versao = select(VersaoProcesso).where(
            VersaoProcesso.processo_id == data.processo_id,
            VersaoProcesso.is_active == True
        )
        versao = (await self.session.execute(stmt_versao)).scalar_one_or_none()
        
        if not versao:
            raise BusinessError("O processo não possui nenhuma versão ativa.")

        # 3. Criar a Execução (Registro Histórico)
        nova_execucao = Execucao(
            tenant_id=tenant_id,
            processo_id=data.processo_id,
            versao_id=versao.id,
            agente_id=data.agente_id,
            status=StatusExecucaoEnum.QUEUED,
            trigger_type=data.trigger_type,
            input_data=data.input_data
        )
        self.session.add(nova_execucao)
        await self.session.flush() # Para gerar o ID da execução

        # 4. CRUCIAL: Criar o Item na Fila (Workload) para o robô consumir
        # Usamos o nome do processo como nome da fila por padrão
        novo_item = ItemFila(
            tenant_id=tenant_id,
            queue_name=processo.name, # O robô deve escutar esta fila
            status=StatusItemFilaEnum.PENDING,
            priority=PriorityEnum.NORMAL,
            payload=data.input_data, # O robô recebe os inputs aqui
            execucao_id=nova_execucao.id,
            max_retries=3
        )
        self.session.add(novo_item)
        
        await self.session.commit()
        await self.session.refresh(nova_execucao)
        
        return nova_execucao

    async def list_executions(self, tenant_id: UUID, params: ExecutionFilterParams):
        # ... (Manter código existente de listagem - se já houver)
        # Se não tiver implementado ainda, podemos deixar simplificado por enquanto
        pass 
        
    async def get_execution_by_id(self, tenant_id: UUID, execution_id: UUID) -> Execucao:
         stmt = select(Execucao).where(Execucao.id == execution_id, Execucao.tenant_id == tenant_id)
         res = await self.session.execute(stmt)
         return res.scalar_one_or_none()

    async def request_stop(self, tenant_id: UUID, execution_id: UUID) -> bool:
        # Lógica de stop (implementar depois)
        return True

    async def get_summary_stats(self, tenant_id: UUID, days: int) -> ExecutionSummary:
        # Retorna mock ou zero por enquanto para não quebrar a API
        return ExecutionSummary()
    

    async def update_execution_status(
            self, 
            tenant_id: UUID, 
            execution_id: UUID, 
            data: ExecutionUpdate
        ) -> Execucao:
            # 1. Buscar execução
            stmt = select(Execucao).where(
                Execucao.id == execution_id, 
                Execucao.tenant_id == tenant_id
            )
            execucao = (await self.session.execute(stmt)).scalar_one_or_none()
            
            if not execucao:
                raise NotFoundError(resource="Execucao", identifier=execution_id)

            # 2. Atualizar estado da execução
            execucao.status = data.status
            if data.end_time:
                execucao.end_time = data.end_time
            elif data.status in [StatusExecucaoEnum.COMPLETED, StatusExecucaoEnum.FAILED]:
                execucao.end_time = datetime.utcnow()

            self.session.add(execucao)

            # 3. Atualizar o Item da Fila correspondente (Sincronização)
            # O item da fila controla o lock e os retries
            stmt_item = select(ItemFila).where(
                ItemFila.execucao_id == execution_id,
                ItemFila.tenant_id == tenant_id
            )
            item_fila = (await self.session.execute(stmt_item)).scalar_one_or_none()

            if item_fila:
                if data.status == StatusExecucaoEnum.COMPLETED:
                    item_fila.status = StatusItemFilaEnum.COMPLETED
                    item_fila.completed_at = datetime.utcnow()
                    item_fila.locked_by = None # Liberta o robô
                    
                elif data.status == StatusExecucaoEnum.FAILED:
                    # Lógica simplificada: se falhou a execução, falha o item
                    # Opcional: Implementar lógica de retry aqui se desejar
                    item_fila.status = StatusItemFilaEnum.FAILED
                    item_fila.completed_at = datetime.utcnow()
                    item_fila.locked_by = None
                    if data.error_details:
                        item_fila.last_error = str(data.error_details.get("message", ""))

                self.session.add(item_fila)

            await self.session.commit()
            await self.session.refresh(execucao)
            return execucao