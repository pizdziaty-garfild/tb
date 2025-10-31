#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Bot - Entry Point
Produkcyjny bot Telegram z panelem admina, obsługą wielu użytkowników,
odrpornością na problemy czasowe, bezpieczeństwem i czystą architekturą.
"""

import asyncio
import logging
import signal
from contextlib import asynccontextmanager

from core.bot_manager import BotManager
from config.settings import Settings
from infra.logging import setup_logging
from infra.database import DatabaseManager
from infra.telemetry import TelemetryManager


class TelegramBotApplication:
    """Główna aplikacja bota Telegram."""
    
    def __init__(self):
        self.settings = Settings()
        self.logger = setup_logging(self.settings.LOG_LEVEL)
        self.db_manager = None
        self.bot_manager = None
        self.telemetry = None
        self._shutdown_event = asyncio.Event()
        
    async def initialize(self):
        """Inicjalizacja wszystkich komponentów."""
        try:
            self.logger.info("Inicjalizacja aplikacji bota Telegram...")
            
            # Inicjalizacja bazy danych
            self.db_manager = DatabaseManager(self.settings.DB_URL)
            await self.db_manager.initialize()
            
            # Inicjalizacja telemetrii
            self.telemetry = TelemetryManager()
            await self.telemetry.initialize()
            
            # Inicjalizacja managera bota
            self.bot_manager = BotManager(self.settings, self.db_manager, self.telemetry)
            await self.bot_manager.initialize()
            
            self.logger.info("Aplikacja zainicjalizowana pomyślnie")
            
        except Exception as e:
            self.logger.error(f"Błąd inicjalizacji: {e}")
            raise
    
    async def run(self):
        """Uruchomienie aplikacji."""
        try:
            self.logger.info("Uruchamianie bota Telegram...")
            
            # Ustawienie handlerów sygnałów
            self._setup_signal_handlers()
            
            # Uruchomienie bota
            await self.bot_manager.start()
            
            # Oczekiwanie na sygnał zatrzymania
            await self._shutdown_event.wait()
            
        except KeyboardInterrupt:
            self.logger.info("Otrzymano sygnał przerwania...")
        except Exception as e:
            self.logger.error(f"Błąd podczas działania bota: {e}")
            raise
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Bezpieczne zatrzymanie aplikacji."""
        self.logger.info("Zatrzymywanie aplikacji...")
        
        try:
            if self.bot_manager:
                await self.bot_manager.stop()
            
            if self.telemetry:
                await self.telemetry.shutdown()
            
            if self.db_manager:
                await self.db_manager.close()
                
            self.logger.info("Aplikacja zatrzymana pomyślnie")
            
        except Exception as e:
            self.logger.error(f"Błąd podczas zatrzymywania: {e}")
    
    def _setup_signal_handlers(self):
        """Ustawienie handlerów sygnałów systemowych."""
        def signal_handler(sig, frame):
            self.logger.info(f"Otrzymano sygnał {sig}")
            self._shutdown_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


async def main():
    """Główna funkcja aplikacji."""
    app = TelegramBotApplication()
    
    try:
        await app.initialize()
        await app.run()
    except Exception as e:
        logging.error(f"Krytyczny błąd aplikacji: {e}")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nAplikacja przerwana przez użytkownika")
    except Exception as e:
        print(f"Krytyczny błąd: {e}")
        exit(1)