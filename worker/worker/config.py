# worker/config.py
"""
Configurações do Worker RPA
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv, find_dotenv

# 1. FORÇA O CARREGAMENTO DO .ENV IMEDIATAMENTE
# Tenta carregar do diretório atual ou do diretório do script
#env_path = Path(__file__).parent / ".env"
load_dotenv(find_dotenv())

class WorkerConfig(BaseSettings):
    """Configurações do Worker"""
    
    # Identificação do Worker
    # O Field(alias=...) ajuda o Pydantic a achar a variável mesmo se o nome for diferente
    WORKER_NAME: str = os.getenv("WORKER_NAME", "RPA-Worker-01")
    WORKER_VERSION: str = "1.0.0"
    
    # API do Orquestrador
    ORCHESTRATOR_URL: str = os.getenv("ORCHESTRATOR_URL", "http://localhost:8000")
    
    # --- CREDENCIAIS ---
    # Capturamos diretamente do ambiente já carregado
    API_KEY: str = os.getenv("API_KEY", "")
    TENANT_ID: str = os.getenv("TENANT_ID", "")
    
    # Credenciais do Robô (Lê EMAIL e PASSWORD do .env)
    WORKER_EMAIL: str = os.getenv("EMAIL", "")
    WORKER_PASSWORD: str = os.getenv("PASSWORD", "")

    # Servidor local (controle UI)
    LOCAL_API_HOST: str = "127.0.0.1"
    LOCAL_API_PORT: int = 8765
    
    # Polling e Timeouts
    POLLING_INTERVAL_SECONDS: int = 5
    HEARTBEAT_INTERVAL_SECONDS: int = 30
    MAX_RETRIES: int = 3
    DEFAULT_TIMEOUT_SECONDS: int = 3600
    
    # Caminhos
    AUTOMATION_BASE_PATH: Path = Path("C:/RpaWorker/automations")
    LOG_PATH: Path = Path("C:/RpaWorker/logs")
    
    # Logs
    LOG_LEVEL: str = "INFO"
    LOG_MAX_BYTES: int = 10 * 1024 * 1024 # 10MB
    LOG_BACKUP_COUNT: int = 5

    # Configuração Pydantic para reforçar a leitura
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

config = WorkerConfig()