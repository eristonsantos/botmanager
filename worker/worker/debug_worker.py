import logging
import sys
import time
from config import config
from manager import manager

# 1. Forçar logs para o Console (Terminal)
root = logging.getLogger()
root.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
root.addHandler(handler)

print("🔍 --- DIAGNÓSTICO DO WORKER ---")
print(f"📡 URL Orquestrador: {config.ORCHESTRATOR_URL}")
print(f"🔑 Tenant ID: {config.TENANT_ID}")
print(f"🤖 Worker Name: {config.WORKER_NAME}")
print("--------------------------------")

try:
    # 2. Tentar o Handshake Manualmente
    print("1️⃣ Tentando Autenticação e Registro...")
    success = manager._initial_handshake()
    
    if success:
        print("\n✅ SUCESSO! Conexão estabelecida.")
        print(f"   Token obtido: {manager.access_token[:20]}...")
        print(f"   Agent ID: {manager.agent_id}")
        
        # 3. Testar Heartbeat
        print("\n2️⃣ Enviando Heartbeat de teste...")
        manager._heartbeat_loop() # Vai rodar uma vez e travar ou podemos rodar em thread
        # Nota: O loop é infinito, então só queremos ver se a primeira chamada funciona.
        # Interrompa com Ctrl+C se ver o log "Heartbeat enviado".
    else:
        print("\n❌ FALHA: O Handshake retornou False.")
        print("   Verifique se o usuário robô existe e a senha (API_KEY) está correta.")

except Exception as e:
    print(f"\n💥 ERRO CRÍTICO: {e}")
    import traceback
    traceback.print_exc()