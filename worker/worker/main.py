# worker/main.py
import logging
import uvicorn
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from logging.handlers import RotatingFileHandler
from pydantic import BaseModel
from typing import Optional

from config import config
from manager import manager

# ============================================================================
# LOGGING CONFIG
# ============================================================================
# Garante que a pasta de logs existe
config.LOG_PATH.mkdir(parents=True, exist_ok=True)

# Configura log para ARQUIVO e CONSOLE
logging.basicConfig(
    level=config.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        RotatingFileHandler(
            config.LOG_PATH / "worker.log",
            maxBytes=config.LOG_MAX_BYTES,
            backupCount=config.LOG_BACKUP_COUNT,
            encoding="utf-8"
        ),
        logging.StreamHandler() # Importante para ver no terminal
    ]
)

logger = logging.getLogger(__name__)

# ============================================================================
# API SETUP
# ============================================================================

app = FastAPI(
    title="RPA Worker Control API",
    version=config.WORKER_VERSION
)

# Permite CORS para a UI local
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# SCHEMAS
# ============================================================================

class ConfigUpdate(BaseModel):
    orchestrator_url: Optional[str] = None
    api_key: Optional[str] = None
    tenant_id: Optional[str] = None
    worker_name: Optional[str] = None

# ============================================================================
# ENDPOINTS DE CONTROLE
# ============================================================================

@app.get("/")
async def root():
    return manager.get_status()

@app.post("/start")
async def start_worker():
    """Inicia o processamento do Worker"""
    result = manager.start()
    logger.info(f"Comando START recebido: {result}")
    return result

@app.post("/stop")
async def stop_worker():
    """Para o processamento do Worker"""
    result = manager.stop()
    logger.info(f"Comando STOP recebido: {result}")
    return result

@app.get("/status")
async def get_status():
    """Retorna status detalhado para a UI"""
    return manager.get_status()

@app.post("/kill")
async def kill_execution():
    """Mata execução atual forçadamente"""
    logger.warning("Comando KILL recebido via API")
    result = manager.kill_current_execution()
    if not result.get("killed") and result.get("reason") != "No active execution":
         raise HTTPException(status_code=400, detail=result.get("reason"))
    return result

@app.post("/config")
async def update_config(data: ConfigUpdate):
    """Atualiza configurações e reinicia conexão se necessário"""
    try:
        # Atualiza memória e arquivo .env
        env_lines = []
        if Path(".env").exists():
            env_lines = Path(".env").read_text().splitlines()
        
        new_env_dict = {}
        for line in env_lines:
            if "=" in line:
                k, v = line.split("=", 1)
                new_env_dict[k] = v
        
        # Atualiza valores
        if data.orchestrator_url: 
            config.ORCHESTRATOR_URL = data.orchestrator_url
            new_env_dict["ORCHESTRATOR_URL"] = data.orchestrator_url
            
        if data.api_key: 
            config.API_KEY = data.api_key
            new_env_dict["API_KEY"] = data.api_key
            
        if data.tenant_id: 
            config.TENANT_ID = data.tenant_id
            new_env_dict["TENANT_ID"] = data.tenant_id

        if data.worker_name:
            config.WORKER_NAME = data.worker_name
            new_env_dict["WORKER_NAME"] = data.worker_name

        # Reescreve .env
        env_content = "\n".join([f"{k}={v}" for k, v in new_env_dict.items()])
        Path(".env").write_text(env_content)
        
        # Recarrega configurações internas se necessário
        # (Idealmente reiniciaríamos o serviço, mas aqui atualizamos a ref)
        logger.info("Configurações atualizadas via API")
        
        return {"status": "updated", "requires_restart": True}
        
    except Exception as e:
        logger.error(f"Erro ao atualizar config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# RUNNER
# ============================================================================

if __name__ == "__main__":
    print(f"🚀 Worker API rodando em http://{config.LOCAL_API_HOST}:{config.LOCAL_API_PORT}")
    # Se quiser que o worker já inicie rodando (sem esperar clicar no botão Start da UI):
    # manager.start() 
    uvicorn.run(app, host=config.LOCAL_API_HOST, port=config.LOCAL_API_PORT)