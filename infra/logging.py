# -*- coding: utf-8 -*-
"""
Logging Infrastructure - simplified to avoid structlog processor mismatch
"""
import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional

from config.settings import LogLevel


def setup_logging(log_level: LogLevel = LogLevel.INFO, log_file: str = 'logs/bot.log') -> logging.Logger:
    # Ensure log directory
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.value))

    # Clear existing handlers
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(getattr(logging, log_level.value))
    ch.setFormatter(logging.Formatter('%(asctime)s %(levelname)s [%(name)s] %(message)s', '%Y-%m-%d %H:%M:%S'))
    root_logger.addHandler(ch)

    # Rotating file handler
    fh = logging.handlers.RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8')
    fh.setLevel(getattr(logging, log_level.value))
    fh.setFormatter(logging.Formatter('%(asctime)s %(levelname)s [%(name)s] %(message)s', '%Y-%m-%d %H:%M:%S'))
    root_logger.addHandler(fh)

    return logging.getLogger('telegram_bot')
