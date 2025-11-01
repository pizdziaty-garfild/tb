# -*- coding: utf-8 -*-
import asyncio
import logging

from config.settings import Settings
from infra.shutdown import ShutdownManager

log = logging.getLogger(__name__)

async def run_with_shutdown(main_coro, cleanup_coros=None):
    sm = ShutdownManager()
    loop = asyncio.get_event_loop()
    sm.install(loop)

    if cleanup_coros:
        for fn in cleanup_coros:
            sm.register_cleanup(fn)

    runner = asyncio.create_task(main_coro())
    await sm.wait()
    log.info("Stopping... running cleanup")
    try:
        runner.cancel()
        with asyncio.CancelledError:
            pass
    except Exception:
        pass
    await sm.run_cleanup()
