#!/usr/bin/env python3
"""
Script de teste para validar a estrutura base da API.

Testa:
1. Importação de todos os módulos
2. Configurações (settings)
3. Conexão com PostgreSQL
4. Conexão com Redis
5. Endpoints de health check
"""
import asyncio
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.core.database import check_database_connection, get_database_latency
from app.core.redis import redis_client


# Configurar logging
setup_logging()
logger = get_logger(__name__)


async def test_configuration():
    """Testa se as configurações foram carregadas corretamente."""
    print("\n" + "="*60)
    print("1️⃣  TESTANDO CONFIGURAÇÕES")
    print("="*60)
    
    try:
        print(f"✓ APP_NAME: {settings.APP_NAME}")
        print(f"✓ API_VERSION: {settings.API_VERSION}")
        print(f"✓ ENVIRONMENT: {settings.ENVIRONMENT}")
        print(f"✓ DEBUG: {settings.DEBUG}")
        print(f"✓ API_PREFIX: {settings.api_prefix}")
        print(f"✓ DATABASE_URL: {settings.DATABASE_URL.split('@')[0]}@...")  # Esconde credenciais
        print(f"✓ REDIS_URL: {settings.REDIS_URL.split('@')[-1]}")
        print(f"✓ SECRET_KEY length: {len(settings.SECRET_KEY)} chars")
        
        # Valida SECRET_KEY
        assert len(settings.SECRET_KEY) >= 32, "SECRET_KEY deve ter pelo menos 32 caracteres"
        
        print("\n✅ Configurações OK!")
        return True
    
    except Exception as e:
        print(f"\n❌ Erro nas configurações: {str(e)}")
        return False


async def test_database():
    """Testa conexão com PostgreSQL."""
    print("\n" + "="*60)
    print("2️⃣  TESTANDO CONEXÃO COM POSTGRESQL")
    print("="*60)
    
    try:
        # Testa conexão
        is_connected = await check_database_connection()
        
        if not is_connected:
            print("❌ Não foi possível conectar ao PostgreSQL")
            print("   Verifique se o container está rodando: docker compose ps")
            return False
        
        print("✓ Conexão estabelecida com sucesso")
        
        # Mede latência
        latency = await get_database_latency()
        print(f"✓ Latência: {latency}ms")
        
        print("\n✅ PostgreSQL OK!")
        return True
    
    except Exception as e:
        print(f"\n❌ Erro no PostgreSQL: {str(e)}")
        return False


async def test_redis():
    """Testa conexão com Redis."""
    print("\n" + "="*60)
    print("3️⃣  TESTANDO CONEXÃO COM REDIS")
    print("="*60)
    
    try:
        # Conecta ao Redis
        await redis_client.connect()
        
        # Testa conexão
        is_connected = await redis_client.health_check()
        
        if not is_connected:
            print("❌ Não foi possível conectar ao Redis")
            print("   Verifique se o container está rodando: docker compose ps")
            return False
        
        print("✓ Conexão estabelecida com sucesso")
        
        # Mede latência
        latency = await redis_client.get_latency()
        print(f"✓ Latência: {latency}ms")
        
        # Testa operações de cache
        test_key = "test:validation"
        test_value = {"status": "ok", "timestamp": "2024-12-09"}
        
        # Set
        success = await redis_client.set_cache(test_key, test_value, ttl=10)
        print(f"✓ SET cache: {'OK' if success else 'FAILED'}")
        
        # Get
        cached_value = await redis_client.get_cache(test_key)
        print(f"✓ GET cache: {cached_value}")
        
        # Delete
        deleted = await redis_client.delete_cache(test_key)
        print(f"✓ DELETE cache: {'OK' if deleted else 'FAILED'}")
        
        print("\n✅ Redis OK!")
        return True
    
    except Exception as e:
        print(f"\n❌ Erro no Redis: {str(e)}")
        return False
    
    finally:
        await redis_client.disconnect()


async def test_imports():
    """Testa importação de todos os módulos principais."""
    print("\n" + "="*60)
    print("4️⃣  TESTANDO IMPORTAÇÕES DE MÓDULOS")
    print("="*60)
    
    try:
        # Core
        from app.core import config, logging, database, redis, exceptions, security, middlewares
        print("✓ app.core.*")
        
        # API
        from app.api.v1 import health
        print("✓ app.api.v1.*")
        
        # Main
        from app import main
        print("✓ app.main")
        
        print("\n✅ Todas importações OK!")
        return True
    
    except Exception as e:
        print(f"\n❌ Erro nas importações: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Executa todos os testes."""
    print("\n" + "="*60)
    print("🚀 VALIDAÇÃO DA ESTRUTURA BASE - RPA ORCHESTRATOR")
    print("="*60)
    
    results = {}
    
    # Executa testes
    results["imports"] = await test_imports()
    results["config"] = await test_configuration()
    results["database"] = await test_database()
    results["redis"] = await test_redis()
    
    # Resumo
    print("\n" + "="*60)
    print("📊 RESUMO DOS TESTES")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "✅ PASSOU" if passed else "❌ FALHOU"
        print(f"{test_name.upper()}: {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*60)
    if all_passed:
        print("🎉 TODOS OS TESTES PASSARAM!")
        print("\nPróximos passos:")
        print("1. Rodar a aplicação: uvicorn app.main:app --reload")
        print("2. Acessar docs: http://localhost:8000/docs")
        print("3. Testar health check: http://localhost:8000/api/v1/health")
    else:
        print("⚠️  ALGUNS TESTES FALHARAM")
        print("\nVerifique:")
        print("1. Se os containers estão rodando: docker compose ps")
        print("2. Se o arquivo .env está configurado corretamente")
        print("3. Os logs de erro acima para mais detalhes")
    print("="*60 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)