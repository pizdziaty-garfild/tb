# -*- coding: utf-8 -*-
"""
Konfiguracja aplikacji
Zarządzanie wszystkimi ustawieniami i zmiennymi środowiskowymi.
"""

import os
from typing import List, Optional
from decouple import config
from enum import Enum


class LogLevel(str, Enum):
    """Poziomy logowania."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class BotMode(str, Enum):
    """Tryby pracy bota."""
    POLLING = "polling"
    WEBHOOK = "webhook"


class Settings:
    """Konfiguracja aplikacji."""
    
    # Bot Configuration
    BOT_TOKEN: str = config('BOT_TOKEN')
    BOT_MODE: BotMode = BotMode(config('BOT_MODE', default='polling'))
    
    # Admin Configuration
    ADMIN_USERS: List[int] = [
        int(x.strip()) for x in config('ADMIN_USERS', default='').split(',')
        if x.strip() and x.strip().isdigit()
    ]
    OWNER_ID: Optional[int] = config('OWNER_ID', cast=int, default=None)
    ADMIN_COMMAND: str = config('ADMIN_COMMAND', default='pusher')
    
    # Time Configuration
    TIMEZONE: str = config('TIMEZONE', default='Europe/Warsaw')
    DEFAULT_INTERVAL: int = config('DEFAULT_INTERVAL', cast=int, default=300)
    DST_SAFE_MODE: bool = config('DST_SAFE_MODE', cast=bool, default=True)
    
    # Database Configuration
    DB_URL: str = config('DB_URL', default='sqlite+aiosqlite:///./data/bot.db')
    DB_POOL_SIZE: int = config('DB_POOL_SIZE', cast=int, default=10)
    DB_MAX_OVERFLOW: int = config('DB_MAX_OVERFLOW', cast=int, default=20)
    
    # Security Configuration
    ENC_MASTER_KEY: str = config('ENC_MASTER_KEY')
    SESSION_TIMEOUT: int = config('SESSION_TIMEOUT', cast=int, default=3600)
    MAX_SESSIONS_PER_USER: int = config('MAX_SESSIONS_PER_USER', cast=int, default=5)
    
    # Rate Limiting Configuration
    RATE_LIMIT_RPS: float = config('RATE_LIMIT_RPS', cast=float, default=1.0)
    RATE_LIMIT_BURST: int = config('RATE_LIMIT_BURST', cast=int, default=5)
    FLOOD_CONTROL_THRESHOLD: int = config('FLOOD_CONTROL_THRESHOLD', cast=int, default=10)
    FLOOD_CONTROL_WINDOW: int = config('FLOOD_CONTROL_WINDOW', cast=int, default=60)
    
    # Webhook Configuration (production)
    WEBHOOK_HOST: str = config('WEBHOOK_HOST', default='localhost')
    WEBHOOK_PORT: int = config('WEBHOOK_PORT', cast=int, default=8443)
    WEBHOOK_PATH: str = config('WEBHOOK_PATH', default='/webhook')
    WEBHOOK_URL: str = config('WEBHOOK_URL', default='')
    
    # TLS Configuration
    TLS_CERT_PATH: str = config('TLS_CERT_PATH', default='certs/cert.pem')
    TLS_KEY_PATH: str = config('TLS_KEY_PATH', default='certs/private.key')
    
    # Logging Configuration
    LOG_LEVEL: LogLevel = LogLevel(config('LOG_LEVEL', default='INFO'))
    LOG_FILE: str = config('LOG_FILE', default='logs/bot.log')
    LOG_MAX_SIZE: int = config('LOG_MAX_SIZE', cast=int, default=10*1024*1024)  # 10MB
    LOG_BACKUP_COUNT: int = config('LOG_BACKUP_COUNT', cast=int, default=5)
    
    # Redis Configuration (optional)
    REDIS_URL: str = config('REDIS_URL', default='redis://localhost:6379/0')
    REDIS_ENABLED: bool = config('REDIS_ENABLED', cast=bool, default=False)
    
    # Telemetry Configuration
    TELEMETRY_ENABLED: bool = config('TELEMETRY_ENABLED', cast=bool, default=True)
    HEALTH_CHECK_INTERVAL: int = config('HEALTH_CHECK_INTERVAL', cast=int, default=300)
    
    # Development Configuration
    DEBUG: bool = config('DEBUG', cast=bool, default=False)
    TESTING: bool = config('TESTING', cast=bool, default=False)
    
    # Contact Information
    CONTACT_INFO: str = config('CONTACT_INFO', default='Administrator')
    
    def __init__(self):
        """Walidacja konfiguracji."""
        self._validate_config()
    
    def _validate_config(self):
        """Walidacja konfiguracji."""
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN jest wymagany")
        
        if not self.ENC_MASTER_KEY:
            raise ValueError("ENC_MASTER_KEY jest wymagany")
        
        if len(self.ENC_MASTER_KEY) < 32:
            raise ValueError("ENC_MASTER_KEY musi mieć co najmniej 32 znaki")
        
        if self.BOT_MODE == BotMode.WEBHOOK and not self.WEBHOOK_URL:
            raise ValueError("WEBHOOK_URL jest wymagany w trybie webhook")
        
        if self.OWNER_ID and self.OWNER_ID not in self.ADMIN_USERS:
            self.ADMIN_USERS.insert(0, self.OWNER_ID)
        
        # Tworzenie katalogów
        os.makedirs(os.path.dirname(self.LOG_FILE), exist_ok=True)
        if 'sqlite' in self.DB_URL:
            os.makedirs(os.path.dirname(self.DB_URL.split('///')[-1]), exist_ok=True)
    
    @property
    def is_development(self) -> bool:
        """Sprawdza czy aplikacja działa w trybie deweloperskim."""
        return self.DEBUG or self.TESTING
    
    @property
    def is_webhook_mode(self) -> bool:
        """Sprawdza czy bot działa w trybie webhook."""
        return self.BOT_MODE == BotMode.WEBHOOK
    
    @property
    def full_webhook_url(self) -> str:
        """Pełny URL webhooka."""
        if not self.is_webhook_mode:
            return ''
        return f"{self.WEBHOOK_URL.rstrip('/')}{self.WEBHOOK_PATH}"
    
    def get_admin_users_str(self) -> str:
        """Zwraca listę administratorów jako string."""
        return ', '.join(map(str, self.ADMIN_USERS))
    
    def is_admin(self, user_id: int) -> bool:
        """Sprawdza czy użytkownik jest administratorem."""
        return user_id in self.ADMIN_USERS
    
    def is_owner(self, user_id: int) -> bool:
        """Sprawdza czy użytkownik jest właścicielem."""
        return self.OWNER_ID and user_id == self.OWNER_ID