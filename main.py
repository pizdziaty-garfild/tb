#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Bot - Entry Point
Produkcyjny bot Telegram z panelem admina, obsługą wielu użytkowników,
odrpornością na problemy czasowe, bezpieczeństwem i czystą architekturą.
"""

import asyncio
import logging

from core.bot_manager import BotManager
from config.settings import Settings
from infra.logging import setup_logging
from infra.database import DatabaseManager
from infra.telemetry import TelemetryManager
from infra.runner import run_with_shutdown


class TelegramBotApplication:
    """Główna aplikacja bota Telegram."""

    def __init__(self):
        self.settings = Settings()
        self.logger = setup_logging(self.settings.LOG_LEVEL)
        self.db_manager = None
        self.bot_manager = None
        self.telemetry = None

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

    async def start(self):
        await self.bot_manager.start()

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


async def main():
    """Główna funkcja aplikacji."""
    app = TelegramBotApplication()

    async def _run():
        await app.initialize()
        await app.start()

    await run_with_shutdown(_run, cleanup_coros=[app.shutdown])


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nAplikacja przerwana przez użytkownika")
    except Exception as e:
        print(f"Krytyczny błąd: {e}")
        raise
