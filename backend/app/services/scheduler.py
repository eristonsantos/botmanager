# backend/app/services/scheduler.py
import asyncio
from datetime import datetime
from uuid import UUID
from croniter import croniter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.database import async_session_maker
from app.core.logging import get_logger
from app.models.governance import Agendamento
from app.models.core import TriggerTypeEnum
from app.services.execution_service import ExecutionService
from app.schemas.execution import ExecutionCreate

logger = get_logger(__name__)

async def process_due_schedules():
    """
    Verifica agendamentos vencidos (next_run <= now) e dispara as execuções.
    """
    async with async_session_maker() as session:
        try:
            # 1. Buscar agendamentos ativos que já deveriam ter rodado
            now = datetime.utcnow()
            stmt = select(Agendamento).where(
                Agendamento.is_active == True,
                Agendamento.next_run <= now,
                Agendamento.process_id.is_not(None) # Garante que tem processo vinculado
            )
            result = await session.execute(stmt)
            schedules = result.scalars().all()

            if not schedules:
                return # Nada para fazer

            logger.info(f"⏰ Scheduler: Encontrados {len(schedules)} agendamentos para processar.")

            for schedule in schedules:
                await _trigger_and_update(session, schedule)

        except Exception as e:
            logger.error(f"💥 Erro no ciclo do Scheduler: {e}")

async def _trigger_and_update(session: AsyncSession, schedule: Agendamento):
    """Executa a lógica de disparo e atualiza a próxima data"""
    try:
        logger.info(f"🚀 Disparando agendamento: {schedule.name} (ID: {schedule.id})")
        
        # 2. Instancia o serviço e cria a execução (Gera Job + Item na Fila)
        service = ExecutionService(session)
        
        # Cria o payload de disparo
        execution_data = ExecutionCreate(
            processo_id=schedule.process_id,
            trigger_type=TriggerTypeEnum.CRON,
            input_data={
                "source": "scheduler",
                "schedule_name": schedule.name,
                "triggered_at": datetime.utcnow().isoformat()
            }
        )
        
        # Dispara! (Isso cria a Execução e o Item na Fila 'Pending')
        await service.trigger_manual_execution(schedule.tenant_id, execution_data)
        
        # 3. Sucesso: Atualiza Last Run e Next Run
        schedule.last_run = datetime.utcnow()
        _update_next_run(schedule)
        
        session.add(schedule)
        await session.commit()
        logger.info(f"✅ Agendamento {schedule.name} processado. Próxima: {schedule.next_run}")

    except Exception as e:
        logger.error(f"❌ Falha ao processar agendamento {schedule.name}: {e}")
        # Importante: Mesmo com erro, atualizamos o next_run para não travar o scheduler em loop infinito
        try:
            _update_next_run(schedule)
            session.add(schedule)
            await session.commit()
        except:
            pass

def _update_next_run(schedule: Agendamento):
    """Calcula a próxima data baseada no CRON"""
    try:
        iter = croniter(schedule.cron_expression, datetime.utcnow())
        schedule.next_run = iter.get_next(datetime)
    except Exception as e:
        logger.error(f"Erro ao calcular CRON para {schedule.name}: {e}")
        # Se falhar o cálculo, joga para longe para não travar (ex: 1 dia)
        # Em produção, deveria desativar o agendamento
        pass

async def start_scheduler():
    """Loop principal que roda em background"""
    logger.info("⏳ Inicializando RPA Scheduler Service...")
    while True:
        try:
            await process_due_schedules()
        except Exception as e:
            logger.error(f"Erro crítico no loop do Scheduler: {e}")
        
        # Verifica a cada 30 segundos
        await asyncio.sleep(30)