# -*- coding: utf-8 -*-
"""
Runner with Windows-friendly Ctrl+C and keyboard 'q' fallback to stop.
"""
import asyncio
import logging
import sys
import signal
from typing import Callable, Awaitable, List

log = logging.getLogger(__name__)

class _Closer:
    def __init__(self):
        self._event = asyncio.Event()
        self._cleanups: List[Callable[[], Awaitable[None]] | Callable[[], None]] = []

    def install_signals(self, loop: asyncio.AbstractEventLoop):
        try:
            loop.add_signal_handler(signal.SIGINT, self.trigger)
            loop.add_signal_handler(signal.SIGTERM, self.trigger)
        except NotImplementedError:
            def _h(sig, frame):
                self.trigger()
            signal.signal(signal.SIGINT, _h)
            try:
                signal.signal(signal.SIGTERM, _h)
            except Exception:
                pass

    def register(self, fn):
        self._cleanups.append(fn)

    def trigger(self):
        if not self._event.is_set():
            log.info("Shutdown requested")
            self._event.set()

    async def wait(self):
        await self._event.wait()

    async def cleanup(self):
        for fn in self._cleanups:
            try:
                res = fn()
                if asyncio.iscoroutine(res):
                    await res
            except Exception as e:
                log.error(f"Cleanup error: {e}")

async def _keyboard_watcher(closer: _Closer):
    """Fallback: press 'q' + Enter to quit."""
    loop = asyncio.get_event_loop()
    def _readline():
        return sys.stdin.readline()
    try:
        while not closer._event.is_set():
            line = await loop.run_in_executor(None, _readline)
            if not line:
                continue
            if line.strip().lower() == 'q':
                closer.trigger()
                break
    except Exception:
        pass

async def run_with_shutdown(main_coro: Callable[[], Awaitable[None]], cleanup_coros: List[Callable[[], Awaitable[None]] | Callable[[], None]] | None = None):
    closer = _Closer()
    loop = asyncio.get_event_loop()
    closer.install_signals(loop)
    if cleanup_coros:
        for fn in cleanup_coros:
            closer.register(fn)

    task = asyncio.create_task(main_coro())
    kb = asyncio.create_task(_keyboard_watcher(closer))

    await closer.wait()
    log.info("Stopping... running cleanup")
    try:
        task.cancel()
        with asyncio.CancelledError:
            pass
    except Exception:
        pass
    await closer.cleanup()
    try:
        kb.cancel()
    except Exception:
        pass
