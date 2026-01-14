# backend/create_admin.py
import asyncio
import os
from uuid import uuid4
from dotenv import load_dotenv

# 1. Carrega variáveis de ambiente (.env)
load_dotenv()

# 2. Imports do Core
from app.core.database import get_session, create_db_and_tables
from sqlalchemy import select

# 3. Importação da função de Hash (com fallback para compatibilidade)
try:
    from app.core.security.auth import hash_password
except ImportError:
    try:
        from app.core.security.password import hash_password
    except ImportError:
        # Último recurso: tenta achar onde estiver
        from app.core.security import get_password_hash as hash_password

# 4. IMPORTAÇÃO MÁGICA: Carrega TODOS os modelos de uma vez
# Isso garante que o SQLModel conheça Agendamento, Processo, Asset, etc.
try:
    from app.models import (
        User, Tenant, 
        Asset, Credencial, Agendamento,
        Processo, Agente,
        ItemFila
    )
    print("✅ Todos os modelos foram carregados corretamente.")
except ImportError as e:
    print(f"❌ ERRO CRÍTICO DE IMPORTAÇÃO: {e}")
    print("Verifique se backend/app/models/__init__.py exporta todas as classes.")
    exit(1)

async def main():
    print("\n🚀 --- INICIANDO SETUP DO BANCO DE DADOS ---")
    
    # 5. FORÇA A CRIAÇÃO DAS TABELAS
    # Isso resolve o erro "relation does not exist"
    print("🛠️  Etapa 1: Criando tabelas no Banco de Dados...")
    try:
        await create_db_and_tables()
        print("✅ Tabelas criadas/verificadas com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao criar tabelas: {e}")
        print("Dica: Se for erro de Enum/Alteração, tente apagar o banco e rodar de novo.")
        return

    # 6. POPULAR DADOS
    print("👤 Etapa 2: Criando Admin e Tenant...")
    async for session in get_session():
        try:
            # --- TENANT ---
            tenant_name = "Cognit Corp"
            stmt = select(Tenant).where(Tenant.name == tenant_name)
            tenant = (await session.execute(stmt)).scalar_one_or_none()
            
            if not tenant:
                tenant = Tenant(id=uuid4(), name=tenant_name)
                session.add(tenant)
                await session.commit()
                await session.refresh(tenant)
                print(f"   ✅ Tenant criado: {tenant_name}")
            else:
                print(f"   ℹ️  Tenant já existe: {tenant_name}")

            # --- USUÁRIO ADMIN ---
            email = "admin@cognit.com"
            password = "Admin123!" 
            stmt_user = select(User).where(User.email == email)
            user = (await session.execute(stmt_user)).scalar_one_or_none()
            
            if not user:
                user = User(
                    id=uuid4(),
                    email=email,
                    hashed_password=hash_password(password),
                    full_name="Super Admin",
                    is_active=True,
                    is_superuser=True,
                    tenant_id=tenant.id
                )
                session.add(user)
                await session.commit()
                print(f"   ✅ Super Usuário criado.")
            else:
                # Atualiza a senha para garantir que você consiga entrar
                user.hashed_password = hash_password(password)
                session.add(user)
                await session.commit()
                print(f"   🔄 Senha do Admin resetada para o padrão.")

            print("\n🎉 --- SETUP CONCLUÍDO COM SUCESSO! ---")
            print(f"👉 Login: {email}")
            print(f"👉 Senha: {password}")
            
        except Exception as e:
            print(f"❌ Erro durante a criação de dados: {e}")
            await session.rollback()
            raise

if __name__ == "__main__":
    asyncio.run(main())