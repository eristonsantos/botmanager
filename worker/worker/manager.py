# worker/manager.py
"""
Gerenciador principal do Worker - Versão Conectada ao Backend
"""
import logging
import time
import json
import httpx
from threading import Thread, Event
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID

from config import config
from automation_runner import AutomationRunner

logger = logging.getLogger(__name__)

class WorkerManager:
    """Gerencia ciclo de vida do Worker e comunicação com Orquestrador"""
    
    def __init__(self):
        self.running = False
        self.stop_event = Event()
        self.current_execution: Optional[AutomationRunner] = None
        
        # Threads
        self.polling_thread: Optional[Thread] = None
        self.heartbeat_thread: Optional[Thread] = None
        
        # Estado Local
        self.last_heartbeat: Optional[datetime] = None
        self.stats = {
            "executions_completed": 0,
            "executions_failed": 0,
            "started_at": None
        }
        
        # Dados de Sessão
        self.access_token: Optional[str] = None
        self.agent_id: Optional[str] = None
        
        # Cliente HTTP (Reutilizável)
        self.client = httpx.Client(
            base_url=config.ORCHESTRATOR_URL,
            timeout=10.0,
            verify=False # Em dev ignoramos SSL
        )

    def start(self) -> Dict[str, Any]:
        """Inicia o worker"""
        if self.running:
            return {"status": "already_running"}
        
        logger.info(f"🚀 Iniciando Worker: {config.WORKER_NAME}")
        
        # 1. Tenta Conexão Inicial (Auth + Registro)
        if not self._initial_handshake():
            logger.error("❌ Falha no handshake inicial. O Worker tentará novamente em background.")
        
        self.running = True
        self.stop_event.clear()
        self.stats["started_at"] = datetime.utcnow().isoformat()
        
        # 2. Inicia Threads
        self.polling_thread = Thread(target=self._polling_loop, daemon=True)
        self.polling_thread.start()
        
        self.heartbeat_thread = Thread(target=self._heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()
        
        return {"status": "started"}

    def stop(self) -> Dict[str, Any]:
        """Para o worker"""
        logger.info("🛑 Parando Worker...")
        self.running = False
        self.stop_event.set()
        
        # Mata execução atual se houver
        if self.current_execution and self.current_execution.status == "running":
            self.current_execution.kill()
            
        return {"status": "stopped"}

    # =========================================================================
    # LÓGICA DE CONEXÃO (HANDSHAKE)
    # =========================================================================

    def _get_headers(self) -> Dict[str, str]:
        """Retorna headers autenticados"""
        headers = {
            "Content-Type": "application/json",
            "X-Tenant-ID": config.TENANT_ID
        }
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def _initial_handshake(self) -> bool:
            """
            Realiza autenticação e busca/cria o Agente no backend.
            """
            try:
                # 1. VALIDAÇÃO PRÉVIA
                # Precisamos decidir qual senha usar (a explícita PASSWORD ou a antiga API_KEY)
                user_email = config.WORKER_EMAIL
                user_pass = config.WORKER_PASSWORD or config.API_KEY
                
                if not user_email or not user_pass:
                    logger.error("❌ Erro: EMAIL e PASSWORD (ou API_KEY) são obrigatórios no .env")
                    return False

                logger.info(f"🔐 Tentando login como: {user_email}")

                # 2. LOGIN (Para pegar Token JWT)
                # O backend espera: email, password e opcionalmente tenant_slug
                login_payload = {
                    "email": user_email,
                    "password": user_pass,
                    # Se tivermos o TENANT_ID ou Slug, ajuda, mas o login básico é email/senha
                }
                
                auth_resp = self.client.post("/api/v1/auth/login", json=login_payload)
                
                if auth_resp.status_code == 401:
                    logger.error(f"❌ Login falhou: Credenciais inválidas para {user_email}")
                    return False
                    
                auth_resp.raise_for_status()
                
                data = auth_resp.json()
                self.access_token = data.get("access_token")
                logger.info("✅ Autenticação realizada com sucesso (Token JWT obtido)")

                # 3. REGISTRAR/BUSCAR AGENTE
                # Agora que estamos logados, o backend sabe quem somos e qual nosso Tenant
                agent_payload = {
                    "name": config.WORKER_NAME,
                    "machine_name": config.WORKER_NAME,
                    "ip_address": "127.0.0.1",
                    "version": config.WORKER_VERSION,
                    "status": "online",
                    "capabilities": ["python", "ui_automation"]
                }
                
                # Tenta criar (POST)
                try:
                    reg_resp = self.client.post(
                        "/api/v1/agents", 
                        json=agent_payload, 
                        headers=self._get_headers()
                    )
                    if reg_resp.status_code == 201:
                        self.agent_id = reg_resp.json().get("id")
                        logger.info(f"✅ Agente registrado novo ID: {self.agent_id}")
                        return True
                except httpx.HTTPStatusError as e:
                    if e.response.status_code != 409: # 409 = Conflict (já existe)
                        raise e
                
                # Se já existe (409), buscamos na lista (GET)
                logger.info("Agente já existe, buscando ID...")
                list_resp = self.client.get(
                    f"/api/v1/agents?machine_name={config.WORKER_NAME}",
                    headers=self._get_headers()
                )
                list_resp.raise_for_status()
                items = list_resp.json().get("items", [])
                
                # Filtra pelo nome exato para garantir
                target_agent = next((a for a in items if a.get("name") == config.WORKER_NAME), None)
                
                if target_agent:
                    self.agent_id = target_agent.get("id")
                    logger.info(f"✅ Agente recuperado ID: {self.agent_id}")
                    return True
                else:
                    logger.error(f"❌ Erro: Agente '{config.WORKER_NAME}' existe mas não foi encontrado na busca.")
                    return False

            except Exception as e:
                logger.error(f"⚠️ Erro no Handshake: {e}")
                return False

    # =========================================================================
    # LOOPS DE SERVIÇO
    # =========================================================================

    def _heartbeat_loop(self):
        """Envia sinal de vida periodicamente"""
        logger.info("💓 Iniciando Loop de Heartbeat")
        
        while self.running and not self.stop_event.is_set():
            try:
                if not self.access_token or not self.agent_id:
                    self._initial_handshake()
                    time.sleep(5)
                    continue

                # Payload do Heartbeat
                status_agente = "busy" if self.current_execution else "online"
                payload = {
                    "status": status_agente,
                    "message": "Worker operante",
                    "extra_data": {
                        "cpu_usage": 0, # Poderia usar psutil aqui
                        "memory_usage": 0
                    }
                }

                resp = self.client.post(
                    f"/api/v1/agents/{self.agent_id}/heartbeat",
                    json=payload,
                    headers=self._get_headers()
                )
                
                if resp.status_code == 200:
                    self.last_heartbeat = datetime.utcnow()
                    logger.debug(f"💓 Heartbeat enviado ({status_agente})")
                elif resp.status_code == 401:
                    logger.warning("Token expirado no Heartbeat. Renovando...")
                    self.access_token = None # Força re-login
                
            except Exception as e:
                logger.error(f"Erro no Heartbeat: {e}")
            
            # Aguarda próximo ciclo
            self.stop_event.wait(config.HEARTBEAT_INTERVAL_SECONDS)

    def _polling_loop(self):
        """Busca novas tarefas na fila"""
        logger.info("👀 Iniciando Loop de Polling")
        
        while self.running and not self.stop_event.is_set():
            try:
                # Se já estiver executando algo, espera terminar
                if self.current_execution:
                    time.sleep(2)
                    continue

                if not self.access_token:
                    time.sleep(2)
                    continue

                # Busca item na fila (endpoint hipotético /workload/get-next)
                # Baseado no workload.py do backend
                resp = self.client.post(
                    "/api/v1/workload/get-next",
                    params={"queue_name": "default"}, # Fila padrão
                    headers=self._get_headers()
                )
                
                if resp.status_code == 200:
                    item = resp.json()
                    if item:
                        logger.info(f"📥 Nova tarefa recebida! ID: {item.get('id')}")
                        self._execute_task(item)
                    else:
                        # Fila vazia
                        pass
                
                elif resp.status_code == 401:
                    self.access_token = None
            
            except Exception as e:
                logger.error(f"Erro no Polling: {e}")
                time.sleep(5) # Backoff em erro
            
            # Intervalo de polling
            self.stop_event.wait(config.POLLING_INTERVAL_SECONDS)

    def _execute_task(self, item: Dict[str, Any]):
        """Executa a automação"""
        try:
            # Extrai dados do payload
            payload = item.get("payload", {})
            execution_id = str(item.get("execucao_id") or item.get("id"))
            
            # Determina qual script rodar
            script_name = payload.get("script_name", "main.py")
            script_path = config.AUTOMATION_BASE_PATH / script_name
            
            logger.info(f"⚙️ Executando Script: {script_path}")
            
            # Instancia e roda o Runner
            runner = AutomationRunner(
                execution_id=execution_id,
                script_path=str(script_path),
                timeout=config.DEFAULT_TIMEOUT_SECONDS
            )
            self.current_execution = runner
            
            # Função wrapper para rodar em thread sem bloquear o manager
            def run_wrapper():
                exit_code, stdout, stderr = runner.run()
                
                # Reporta resultado (Aqui você chamaria o endpoint de update execution)
                self._report_result(execution_id, exit_code, stdout, stderr)
                
                # Limpa estado
                if exit_code == 0:
                    self.stats["executions_completed"] += 1
                else:
                    self.stats["executions_failed"] += 1
                self.current_execution = None
            
            # Inicia execução
            Thread(target=run_wrapper, daemon=True).start()
            
        except Exception as e:
            logger.error(f"Falha ao preparar execução: {e}")
            self.current_execution = None

    def _report_result(self, execution_id: str, exit_code: int, stdout: str, stderr: str):
        """Envia o resultado final para o Backend"""
        try:
            status_final = "completed" if exit_code == 0 else "failed"
            update_payload = {
                "status": status_final,
                "end_time": datetime.utcnow().isoformat(),
                "logs": stdout + "\n" + stderr,
                "error_details": {"message": stderr} if stderr else None
            }
            
            # Chama PATCH /executions/{id}
            self.client.patch(
                f"/api/v1/executions/{execution_id}",
                json=update_payload,
                headers=self._get_headers()
            )
            logger.info(f"📤 Resultado da execução {execution_id} enviado: {status_final}")
            
        except Exception as e:
            logger.error(f"Erro ao reportar resultado: {e}")

    # =========================================================================
    # CONTROLES MANUAIS (UI)
    # =========================================================================

    def get_status(self) -> Dict[str, Any]:
            """Retorna status para a UI"""
            return {
                "running": self.running,
                "worker_name": config.WORKER_NAME,
                "version": config.WORKER_VERSION,
                "has_active_execution": self.current_execution is not None,
                "current_execution_id": self.current_execution.execution_id if self.current_execution else None,
                "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
                "stats": self.stats,
                "config": {
                    # --- CORREÇÃO AQUI ---
                    # Adicionamos todos os campos que o Rust espera na struct WorkerConfig
                    "orchestrator_url": config.ORCHESTRATOR_URL,
                    "polling_interval": config.POLLING_INTERVAL_SECONDS,
                    "heartbeat_interval": config.HEARTBEAT_INTERVAL_SECONDS, # <--- Faltava este!
                    "tenant_id": config.TENANT_ID,
                    "api_key": "***" # Segurança: não enviamos a key real, ou enviamos mascarada se precisar
                }
            }

    def kill_current_execution(self) -> Dict[str, Any]:
        """Mata processo atual"""
        if self.current_execution:
            self.current_execution.kill()
            return {"killed": True, "reason": "User requested"}
        return {"killed": False, "reason": "No active execution"}

# Singleton global
manager = WorkerManager()