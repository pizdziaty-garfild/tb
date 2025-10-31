# -*- coding: utf-8 -*-
"""
Telemetry Manager - healthcheck & simple metrics (minimal stub)
"""
import asyncio
import logging
from typing import Dict

class TelemetryManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._running = False
        self._task = None
        self._metrics: Dict[str, int] = {
            "errors": 0,
            "messages": 0,
            "sessions": 0,
        }

    async def initialize(self):
        return

    async def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())

    async def shutdown(self):
        self._running = False
        if self._task:
            self._task.cancel()

    async def _loop(self):
        while self._running:
            await asyncio.sleep(60)
            self.logger.debug(f"Telemetry heartbeat: {self._metrics}")

    async def record_error(self, msg: str):
        self._metrics["errors"] += 1
        self.logger.error(f"Telemetry error: {msg}")

    def set_sessions(self, count: int):
        self._metrics["sessions"] = count

    def inc_messages(self, n: int = 1):
        self._metrics["messages"] += n

    async def health_check(self) -> Dict[str, str]:
        return {"status": "ok"}
