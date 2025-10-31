# -*- coding: utf-8 -*-
"""
Bot Manager - Główny manager bota Telegram
Zarządza życiem bota, rejestruje handlery i obsługuje pętlę zdarzeń.
"""

import asyncio
import logging
from typing import Optional

from telegram import Bot
from telegram.ext import Application, ContextTypes
from telegram.error import TelegramError

from config.settings import Settings, BotMode
from core.command_bus import CommandBus
from core.user_manager import UserManager
from infra.database import DatabaseManager
from infra.scheduler import SchedulerManager
from infra.rate_limit import RateLimiter
from infra.telemetry import TelemetryManager
from handlers.admin_commands import AdminCommandsHandler
from handlers.user_commands import UserCommandsHandler
from handlers.group_manager import GroupManagerHandler


class BotManager:
    """Główny manager bota Telegram."""
    
    def __init__(self, settings: Settings, db_manager: DatabaseManager, telemetry: TelemetryManager):
        self.settings = settings
        self.db_manager = db_manager
        self.telemetry = telemetry
        self.logger = logging.getLogger(__name__)
        
        # Komponenty
        self.application: Optional[Application] = None
        self.bot: Optional[Bot] = None
        self.command_bus: Optional[CommandBus] = None
        self.user_manager: Optional[UserManager] = None
        self.scheduler: Optional[SchedulerManager] = None
        self.rate_limiter: Optional[RateLimiter] = None
        
        # Handlery
        self.admin_handler: Optional[AdminCommandsHandler] = None
        self.user_handler: Optional[UserCommandsHandler] = None
        self.group_handler: Optional[GroupManagerHandler] = None
        
        self._is_running = False
    
    async def initialize(self):
        """Inicjalizacja managera bota."""
        try:
            self.logger.info("Inicjalizacja managera bota...")
            
            # Tworzenie aplikacji
            self.application = (
                Application.builder()
                .token(self.settings.BOT_TOKEN)
                .build()
            )
            
            self.bot = self.application.bot
            
            # Inicjalizacja komponentów
            await self._initialize_components()
            
            # Rejestracja handlerów
            await self._register_handlers()
            
            # Konfiguracja error handlera
            self.application.add_error_handler(self._error_handler)
            
            self.logger.info("Manager bota zainicjalizowany pomyślnie")
            
        except Exception as e:
            self.logger.error(f"Błąd inicjalizacji managera bota: {e}")
            raise
    
    async def _initialize_components(self):
        """Inicjalizacja wszystkich komponentów."""
        # User Manager
        self.user_manager = UserManager(self.db_manager, self.settings)
        await self.user_manager.initialize()
        
        # Rate Limiter
        self.rate_limiter = RateLimiter(
            max_calls=int(self.settings.RATE_LIMIT_RPS),
            time_window=1.0,
            burst_limit=self.settings.RATE_LIMIT_BURST
        )
        
        # Command Bus
        self.command_bus = CommandBus(self.user_manager, self.rate_limiter)
        
        # Scheduler
        self.scheduler = SchedulerManager(self.settings)
        await self.scheduler.initialize()
        
        # Handlery
        self.admin_handler = AdminCommandsHandler(self.settings, self.db_manager, self.user_manager, self.scheduler)
        self.user_handler = UserCommandsHandler(self.settings, self.user_manager)
        self.group_handler = GroupManagerHandler(self.settings, self.db_manager, self.user_manager)
    
    async def _register_handlers(self):
        """Rejestracja wszystkich handlerów."""
        # Rejestracja handlerów w command bus
        await self.admin_handler.register_handlers(self.application, self.command_bus)
        await self.user_handler.register_handlers(self.application, self.command_bus)
        await self.group_handler.register_handlers(self.application, self.command_bus)
        
        # Rejestracja middleware w aplikacji
        self.application.add_handler(self.command_bus.create_message_handler(), group=-1)
    
    async def start(self):
        """Uruchomienie bota."""
        try:
            self.logger.info(f"Uruchamianie bota w trybie {self.settings.BOT_MODE}...")
            
            if self.settings.is_webhook_mode:
                await self._start_webhook()
            else:
                await self._start_polling()
            
            # Uruchomienie schedulera
            await self.scheduler.start()
            
            self._is_running = True
            self.logger.info("Bot uruchomiony pomyślnie")
            
            # Wysłanie powiadomienia do właściciela
            await self._notify_owner_bot_started()
            
        except Exception as e:
            self.logger.error(f"Błąd uruchamiania bota: {e}")
            raise
    
    async def _start_polling(self):
        """Uruchomienie bota w trybie polling."""
        self.logger.info("Uruchamianie w trybie polling...")
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling(
            drop_pending_updates=True,
            allowed_updates=None
        )
    
    async def _start_webhook(self):
        """Uruchomienie bota w trybie webhook."""
        self.logger.info(f"Uruchamianie w trybie webhook na {self.settings.WEBHOOK_HOST}:{self.settings.WEBHOOK_PORT}...")
        
        await self.application.initialize()
        await self.application.start()
        
        # Ustawienie webhook
        await self.application.updater.start_webhook(
            listen=self.settings.WEBHOOK_HOST,
            port=self.settings.WEBHOOK_PORT,
            url_path=self.settings.WEBHOOK_PATH,
            cert=self.settings.TLS_CERT_PATH if self.settings.TLS_CERT_PATH else None,
            key=self.settings.TLS_KEY_PATH if self.settings.TLS_KEY_PATH else None,
            webhook_url=self.settings.full_webhook_url,
            drop_pending_updates=True
        )
    
    async def stop(self):
        """Zatrzymanie bota."""
        try:
            if not self._is_running:
                return
            
            self.logger.info("Zatrzymywanie bota...")
            
            # Wysłanie powiadomienia do właściciela
            await self._notify_owner_bot_stopping()
            
            # Zatrzymanie schedulera
            if self.scheduler:
                await self.scheduler.stop()
            
            # Zatrzymanie aplikacji
            if self.application:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
            
            self._is_running = False
            self.logger.info("Bot zatrzymany pomyślnie")
            
        except Exception as e:
            self.logger.error(f"Błąd zatrzymywania bota: {e}")
    
    async def _error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Główny handler błędów."""
        self.logger.error(f"Nieobsłużony błąd: {context.error}", exc_info=context.error)
        
        # Rejestracja błędu w telemetrii
        if self.telemetry:
            await self.telemetry.record_error(str(context.error))
        
        # Powiadomienie właściciela o krytycznych błędach
        if self.settings.OWNER_ID and isinstance(context.error, TelegramError):
            try:
                error_msg = f"⚠️ Krytyczny błąd bota:\n```\n{str(context.error)[:1000]}\n```"
                await self.bot.send_message(
                    chat_id=self.settings.OWNER_ID,
                    text=error_msg,
                    parse_mode='Markdown'
                )
            except Exception as e:
                self.logger.error(f"Nie udało się wysłać powiadomienia o błędzie: {e}")
    
    async def _notify_owner_bot_started(self):
        """Powiadomienie właściciela o uruchomieniu bota."""
        if not self.settings.OWNER_ID:
            return
        
        try:
            message = (
                f"✅ **Bot uruchomiony**\n\n"
                f"Tryb: {self.settings.BOT_MODE}\n"
                f"Strefa czasowa: {self.settings.TIMEZONE}\n"
                f"Administratorzy: {len(self.settings.ADMIN_USERS)}\n"
                f"Wersja: 1.0.0"
            )
            
            await self.bot.send_message(
                chat_id=self.settings.OWNER_ID,
                text=message,
                parse_mode='Markdown'
            )
        except Exception as e:
            self.logger.error(f"Nie udało się wysłać powiadomienia o uruchomieniu: {e}")
    
    async def _notify_owner_bot_stopping(self):
        """Powiadomienie właściciela o zatrzymaniu bota."""
        if not self.settings.OWNER_ID:
            return
        
        try:
            message = "⏹️ **Bot zatrzymywany...** Sesje użytkowników zostają zapisane."
            
            await self.bot.send_message(
                chat_id=self.settings.OWNER_ID,
                text=message,
                parse_mode='Markdown'
            )
        except Exception as e:
            self.logger.error(f"Nie udało się wysłać powiadomienia o zatrzymaniu: {e}")
    
    @property
    def is_running(self) -> bool:
        """Sprawdza czy bot jest uruchomiony."""
        return self._is_running