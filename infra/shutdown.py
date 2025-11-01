# -*- coding: utf-8 -*-
"""
Graceful shutdown handling for Windows (Ctrl+C) with PTB Application.
"""
import asyncio
import logging
import signal
from typing import Callable, Awaitable

log = logging.getLogger(__name__)

class ShutdownManager:
    def __init__(self):
        self._closing = asyncio.Event()
        self._cleanup: list[Callable[[], Awaitable[None]] | Callable[[], None]] = []

    def register_cleanup(self, func: Callable[[], Awaitable[None]] | Callable[[], None]):
        self._cleanup.append(func)

    async def wait(self):
        await self._closing.wait()

    def install(self, loop: asyncio.AbstractEventLoop):
        # Windows: signal.SIGINT via default handler may not propagate in some loops
        try:
            loop.add_signal_handler(signal.SIGINT, self.trigger)
            loop.add_signal_handler(signal.SIGTERM, self.trigger)
        except NotImplementedError:
            # Fallback for Windows event loop
            def _win_sigint_handler(sig, frame):
                self.trigger()
            signal.signal(signal.SIGINT, _win_sigint_handler)
            try:
                signal.signal(signal.SIGTERM, _win_sigint_handler)
            except Exception:
                pass

    def trigger(self):
        if not self._closing.is_set():
            log.info("Shutdown requested (Ctrl+C)")
            self._closing.set()

    async def run_cleanup(self):
        for fn in self._cleanup:
            try:
                res = fn()
                if asyncio.iscoroutine(res):
                    await res
            except Exception as e:
                log.error(f"Cleanup error: {e}")
