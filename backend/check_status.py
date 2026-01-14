import asyncio
from uuid import UUID
from app.core.database import get_session_context
from app.models.workload import ItemFila
from sqlmodel import select

# O ID da tarefa que vimos no log do Worker
TASK_ID = "332eacd8-cb9f-4ff5-bca9-7ae93e3df081"

async def check():
    print(f"🔍 Verificando Status da Tarefa: {TASK_ID}...\n")
    
    async with get_session_context() as session:
        # Busca direta no banco (sem depender da API)
        stmt = select(ItemFila).where(ItemFila.id == UUID(TASK_ID))
        result = await session.execute(stmt)
        item = result.scalar_one_or_none()
        
        if item:
            print(f"✅ STATUS: {item.status.value.upper()}") # Esperado: COMPLETED
            print(f"📅 Concluído em: {item.completed_at}")
            print(f"📦 Payload: {item.payload}")
        else:
            print("❌ Tarefa não encontrada no banco!")

if __name__ == "__main__":
    asyncio.run(check())