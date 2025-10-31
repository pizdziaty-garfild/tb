# -*- coding: utf-8 -*-
"""
Logging Infrastructure - Structured logging z rotacją
Konfiguracja logowania dla produkcji z JSON format i rotacją plików.
"""

import logging
import logging.handlers
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

import structlog
from structlog.types import FilteringBoundLogger

from config.settings import LogLevel


class JSONFormatter(logging.Formatter):
    """Formatter JSON dla structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Formatowanie log record do JSON."""
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Dodanie dodatkowych pól jeśli istnieją
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        if hasattr(record, 'session_id'):
            log_data['session_id'] = record.session_id
        if hasattr(record, 'command'):
            log_data['command'] = record.command
        if hasattr(record, 'execution_time_ms'):
            log_data['execution_time_ms'] = record.execution_time_ms
        
        # Dodanie exception info jeśli istnieje
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)


class TelegramBotFilter(logging.Filter):
    """Filter dla logów bota Telegram."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filtrowanie logów."""
        # Pomijanie zbyt szczegółowych logów z external libraries
        if record.name.startswith('httpx'):
            return record.levelno >= logging.WARNING
        if record.name.startswith('urllib3'):
            return record.levelno >= logging.WARNING
        if record.name.startswith('telegram.vendor'):
            return record.levelno >= logging.WARNING
        
        return True


def setup_logging(log_level: LogLevel = LogLevel.INFO, log_file: str = 'logs/bot.log') -> FilteringBoundLogger:
    """Konfiguracja structured logging."""
    
    # Utworzenie katalogu logów
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Skonfigurowanie structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_logger_name,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(log_level.value)),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )
    
    # Konfiguracja root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.value))
    
    # Usunięcie istniejących handlerów
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler z kolorami dla development
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.value))
    
    if log_level == LogLevel.DEBUG:
        # Readable format dla development
        console_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
    else:
        # JSON format dla production
        console_format = JSONFormatter()
    
    console_handler.setFormatter(console_format)
    console_handler.addFilter(TelegramBotFilter())
    root_logger.addHandler(console_handler)
    
    # File handler z rotacją
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(getattr(logging, log_level.value))
    file_handler.setFormatter(JSONFormatter())
    file_handler.addFilter(TelegramBotFilter())
    root_logger.addHandler(file_handler)
    
    # Error file handler - tylko błędy
    error_file_handler = logging.handlers.RotatingFileHandler(
        log_file.replace('.log', '_errors.log'),
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(error_file_handler)
    
    # Zwrócenie structured logger
    return structlog.get_logger('telegram_bot')


class LoggingContext:
    """Context manager dla dodatkowych danych w logach."""
    
    def __init__(self, **kwargs):
        self.context_data = kwargs
        self.old_context = {}
    
    def __enter__(self):
        # Zapisanie starego kontekstu
        for key, value in self.context_data.items():
            if hasattr(logging, '_context'):
                self.old_context[key] = getattr(logging._context, key, None)
                setattr(logging._context, key, value)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Przywrócenie starego kontekstu
        for key, old_value in self.old_context.items():
            if hasattr(logging, '_context'):
                if old_value is None:
                    delattr(logging._context, key)
                else:
                    setattr(logging._context, key, old_value)


def log_with_context(**context_data):
    """Dekorator do dodawania kontekstu do logów."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            with LoggingContext(**context_data):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def setup_telegram_logging():
    """Specjalna konfiguracja dla biblioteki python-telegram-bot."""
    # Zmniejszenie szczegółowości logów telegram
    logging.getLogger('telegram').setLevel(logging.WARNING)
    logging.getLogger('telegram.ext').setLevel(logging.INFO)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    # Włączenie logów dla naszego bota
    logging.getLogger('telegram_bot').setLevel(logging.DEBUG)
    logging.getLogger('core').setLevel(logging.DEBUG)
    logging.getLogger('handlers').setLevel(logging.DEBUG)
    logging.getLogger('infra').setLevel(logging.DEBUG)