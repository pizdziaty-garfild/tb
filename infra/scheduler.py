# -*- coding: utf-8 -*-
"""
Scheduler Manager - DST-safe, retry with jitter (minimal runnable stub)
"""
import asyncio
import logging
from dataclasses import dataclass
from typing import Callable, Dict, Optional
from datetime import datetime, timedelta, timezone

from tenacity import retry, stop_after_attempt, wait_random_exponential

@dataclass
class _Job:
    name: str
    interval_seconds: int
    coro: Callable
    task: Optional[asyncio.Task] = None
    next_run: Optional[datetime] = None

class SchedulerManager:
    def __init__(self, settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        self._jobs: Dict[str, _Job] = {}
        self._running = False
        self._loop_task: Optional[asyncio.Task] = None

    async def initialize(self):
        return

    async def start(self):
        if self._running:
            return
        self._running = True
        self._loop_task = asyncio.create_task(self._runner())
        self.logger.info("Scheduler started")

    async def stop(self):
        self._running = False
        if self._loop_task:
            self._loop_task.cancel()
        for job in self._jobs.values():
            if job.task:
                job.task.cancel()
        self.logger.info("Scheduler stopped")

    def add_interval_job(self, name: str, coro: Callable, minutes: int):
        seconds = max(60, minutes * 60)
        self._jobs[name] = _Job(name=name, interval_seconds=seconds, coro=coro, next_run=self._now())

    async def _runner(self):
        while self._running:
            now = self._now()
            for job in list(self._jobs.values()):
                if job.next_run and now >= job.next_run:
                    job.next_run = now + timedelta(seconds=job.interval_seconds)
                    job.task = asyncio.create_task(self._execute(job))
            await asyncio.sleep(1)

    @retry(stop=stop_after_attempt(5), wait=wait_random_exponential(multiplier=1, max=60))
    async def _execute(self, job: _Job):
        try:
            await job.coro()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            self.logger.error(f"Job {job.name} failed: {e}")
            raise

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)
