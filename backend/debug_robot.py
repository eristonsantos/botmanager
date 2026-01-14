# backend/debug_robot.py
import asyncio
import sys
from sqlmodel import select

# Adiciona o diretório atual ao path para importar 'app'
sys.path.append(".")

from app.core.database import async_session_maker
from app.models import User, Tenant
from app.core.security.password import verify_password, hash_password

async def check_robot():
    TARGET_EMAIL = "robot99@cognit.com"
    TARGET_PASS = "123456"
    
    print(f"\n🔍 Verificando usuário: {TARGET_EMAIL} ...")
    
    async with async_session_maker() as session:
        # 1. Buscar Usuário
        query = select(User).where(User.email == TARGET_EMAIL)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"❌ Usuário NÃO ENCONTRADO no banco de dados.")
            print("\n💡 AÇÃO SUGERIDA: Você precisa criar este usuário.")
            
            # Pergunta se quer criar agora
            create = input("   Deseja criar este usuário (e um tenant Demo) agora? (s/n): ")
            if create.lower() == 's':
                await create_demo_robot(session, TARGET_EMAIL, TARGET_PASS)
            return

        # 2. Verificar Status
        print(f"✅ Usuário encontrado! ID: {user.id}")
        print(f"   Tenant ID: {user.tenant_id}")
        print(f"   Ativo: {user.is_active}")
        
        if not user.is_active:
            print("❌ ERRO: O usuário está marcado como INATIVO (is_active=False).")
            return

        # 3. Verificar Senha
        is_password_valid = verify_password(TARGET_PASS, user.hashed_password)
        if is_password_valid:
            print("✅ Senha CORRETA. O login deveria funcionar.")
        else:
            print("❌ Senha INCORRETA.")
            print(f"   Hash no banco: {user.hashed_password[:10]}...")
            print(f"   Senha testada: {TARGET_PASS}")
            
            fix = input("   Deseja resetar a senha para '123456' agora? (s/n): ")
            if fix.lower() == 's':
                user.hashed_password = hash_password(TARGET_PASS)
                session.add(user)
                await session.commit()
                print("✅ Senha atualizada com sucesso!")

async def create_demo_robot(session, email, password):
    # 1. Verificar/Criar Tenant
    query = select(Tenant).where(Tenant.slug == "demo-tenant")
    tenant = (await session.execute(query)).scalar_one_or_none()
    
    if not tenant:
        print("   Creating 'demo-tenant'...")
        tenant = Tenant(name="Demo Company", slug="demo-tenant")
        session.add(tenant)
        await session.commit()
        await session.refresh(tenant)
    
    # 2. Criar Usuário
    print(f"   Criando usuário {email}...")
    new_user = User(
        email=email,
        full_name="Robot 01",
        hashed_password=hash_password(password),
        tenant_id=tenant.id,
        is_active=True,
        is_superuser=False
    )
    session.add(new_user)
    await session.commit()
    print("✅ Usuário criado com sucesso! Tente rodar o Worker novamente.")

if __name__ == "__main__":
    try:
        asyncio.run(check_robot())
    except Exception as e:
        print(f"Erro ao conectar no banco: {e}")
        print("Verifique se seu .env do BACKEND está correto e se o Docker/Postgres está rodando.")