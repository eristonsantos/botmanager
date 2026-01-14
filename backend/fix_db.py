import asyncio
import os
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

# 1. Carregar variáveis de ambiente
backend_dir = Path(__file__).resolve().parent
env_path = backend_dir / ".env"
load_dotenv(env_path)

DATABASE_URL = os.getenv("DATABASE_URL")

async def nuke_workload_tables():
    if not DATABASE_URL:
        print("❌ Erro: DATABASE_URL não encontrada no .env")
        return

    print(f"🔌 Conectando para limpeza profunda...")
    
    engine = create_async_engine(DATABASE_URL)
    
    try:
        async with engine.begin() as conn:
            print("💣 Derrubando tabelas...")
            await conn.execute(text("DROP TABLE IF EXISTS excecao CASCADE;"))
            await conn.execute(text("DROP TABLE IF EXISTS item_fila CASCADE;"))
            
            print("💣 Derrubando tipos ENUM antigos...")
            # Precisamos apagar os tipos para o Alembic poder recriá-los
            await conn.execute(text("DROP TYPE IF EXISTS statusitemfilaenum CASCADE;"))
            await conn.execute(text("DROP TYPE IF EXISTS tipoexcecaoenum CASCADE;"))
            await conn.execute(text("DROP TYPE IF EXISTS severityenum CASCADE;"))
            
            print("✅ Limpeza completa! O terreno está pronto.")
    except Exception as e:
        print(f"❌ Erro ao limpar: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(nuke_workload_tables())