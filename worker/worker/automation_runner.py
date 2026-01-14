# worker/automation_runner.py
"""
Executor de automações com controle de processo
"""
import subprocess
import psutil
from threading import Timer, Thread
from typing import Optional, Tuple
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class AutomationRunner:
    """Gerencia execução de uma automação Python"""
    
    def __init__(self, execution_id: str, script_path: str, timeout: int = 3600):
        self.execution_id = execution_id
        self.script_path = Path(script_path)
        self.timeout = timeout
        self.process: Optional[subprocess.Popen] = None
        self.timeout_timer: Optional[Timer] = None
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.status = "pending"
        self.pid: Optional[int] = None
        
    def run(self) -> Tuple[int, str, str]:
        """
        Executa a automação e retorna (exit_code, stdout, stderr)
        """
        if not self.script_path.exists():
            raise FileNotFoundError(f"Script não encontrado: {self.script_path}")
        
        logger.info(f"Iniciando execução {self.execution_id}: {self.script_path}")
        
        try:
            # Inicia processo isolado
            self.start_time = datetime.utcnow()
            self.status = "running"
            
            self.process = subprocess.Popen(
                ["python", str(self.script_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,  # Windows
                text=True
            )
            
            self.pid = self.process.pid
            logger.info(f"Processo iniciado: PID {self.pid}")
            
            # Configura timeout automático
            self.timeout_timer = Timer(self.timeout, self._force_kill)
            self.timeout_timer.start()
            
            # Aguarda conclusão
            stdout, stderr = self.process.communicate(timeout=self.timeout)
            self.timeout_timer.cancel()
            
            self.end_time = datetime.utcnow()
            exit_code = self.process.returncode
            
            if exit_code == 0:
                self.status = "completed"
                logger.info(f"Execução {self.execution_id} concluída com sucesso")
            else:
                self.status = "failed"
                logger.error(f"Execução {self.execution_id} falhou: exit code {exit_code}")
            
            return exit_code, stdout, stderr
            
        except subprocess.TimeoutExpired:
            self.status = "timeout"
            logger.error(f"Execução {self.execution_id} timeout após {self.timeout}s")
            self._force_kill()
            return -1, "", "Timeout: execução excedeu tempo limite"
            
        except Exception as e:
            self.status = "error"
            logger.exception(f"Erro na execução {self.execution_id}: {e}")
            self._force_kill()
            return -1, "", str(e)
    
    def kill(self) -> bool:
        """Mata a execução forçadamente"""
        if self.process and self.process.poll() is None:
            logger.warning(f"Matando execução {self.execution_id} (PID {self.pid})")
            self._force_kill()
            return True
        return False
    
    def _force_kill(self):
        """Mata processo e toda a árvore de filhos"""
        if not self.process:
            return
        
        try:
            parent = psutil.Process(self.process.pid)
            children = parent.children(recursive=True)
            
            # Mata filhos primeiro
            for child in children:
                try:
                    logger.debug(f"Matando processo filho: PID {child.pid}")
                    child.kill()
                except psutil.NoSuchProcess:
                    pass
            
            # Mata pai
            logger.debug(f"Matando processo pai: PID {parent.pid}")
            parent.kill()
            
            # Aguarda confirmação
            parent.wait(timeout=5)
            logger.info(f"Processo {self.process.pid} morto com sucesso")
            
        except psutil.NoSuchProcess:
            logger.debug(f"Processo {self.process.pid} já estava morto")
        except psutil.TimeoutExpired:
            logger.error(f"Timeout ao matar processo {self.process.pid}")
        except Exception as e:
            logger.exception(f"Erro ao matar processo: {e}")
        finally:
            self.status = "killed"
            self.end_time = datetime.utcnow()
    
    def get_duration_seconds(self) -> Optional[float]:
        """Retorna duração da execução em segundos"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None