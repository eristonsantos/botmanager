# backend/app/core/logging.py
"""
Sistema de logging estruturado com suporte a correlation ID.
Logs em formato JSON para produção e texto colorido para desenvolvimento.
"""
import logging
import sys
import json
from typing import Any, Dict
from datetime import datetime
from contextvars import ContextVar
import uuid

from app.core.config import settings


# ContextVar para armazenar o correlation_id por request
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


class CorrelationIDFilter(logging.Filter):
    """Adiciona o correlation_id em todos os logs."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id()
        return True


class JSONFormatter(logging.Formatter):
    """Formatter que gera logs em formato JSON estruturado."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", ""),
        }
        
        # Adiciona informações extras
        if hasattr(record, "tenant_id"):
            log_data["tenant_id"] = record.tenant_id
        
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        
        # Adiciona exception info se houver
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Adiciona campos extras passados no log
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)
        
        return json.dumps(log_data, default=str)


class ColoredFormatter(logging.Formatter):
    """Formatter com cores para desenvolvimento."""
    
    # Cores ANSI
    COLORS = {
        "DEBUG": "\033[36m",      # Cyan
        "INFO": "\033[32m",       # Green
        "WARNING": "\033[33m",    # Yellow
        "ERROR": "\033[31m",      # Red
        "CRITICAL": "\033[35m",   # Magenta
    }
    RESET = "\033[0m"
    
    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        correlation_id = getattr(record, "correlation_id", "no-correlation-id")
        
        # Formato: [TIMESTAMP] [LEVEL] [CORRELATION_ID] LOGGER: MESSAGE
        formatted = (
            f"{color}[{self.formatTime(record)}] "
            f"[{record.levelname}] "
            f"[{correlation_id[:8]}...] "  # Primeiros 8 chars do UUID
            f"{record.name}: {record.getMessage()}{self.RESET}"
        )
        
        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"
        
        return formatted


def setup_logging() -> None:
    """
    Configura o sistema de logging da aplicação.
    Usa JSON em produção e texto colorido em desenvolvimento.
    """
    # Remove handlers existentes
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Configura nível de log
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    root_logger.setLevel(log_level)
    
    # Cria handler para stdout
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # Adiciona filtro de correlation ID
    console_handler.addFilter(CorrelationIDFilter())
    
    # Seleciona formatter baseado no ambiente
    if settings.LOG_FORMAT == "json" or settings.is_production:
        formatter = JSONFormatter()
    else:
        formatter = ColoredFormatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Silencia logs verbosos de bibliotecas externas
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_correlation_id() -> str:
    """
    Retorna o correlation_id do contexto atual.
    Se não existir, retorna string vazia (não gera novo para evitar inconsistências).
    """
    return correlation_id_var.get()


def set_correlation_id(correlation_id: str) -> None:
    """Define o correlation_id no contexto atual."""
    correlation_id_var.set(correlation_id)


def generate_correlation_id() -> str:
    """Gera um novo correlation_id único."""
    return str(uuid.uuid4())


def get_logger(name: str) -> logging.Logger:
    """
    Retorna um logger configurado para o módulo especificado.
    
    Args:
        name: Nome do módulo (geralmente __name__)
    
    Returns:
        Logger configurado
    """
    return logging.getLogger(name)


# Configurar logging na importação do módulo
setup_logging()