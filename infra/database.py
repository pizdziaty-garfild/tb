# -*- coding: utf-8 -*-
"""
Database Manager - dual-mode (sync/async) to avoid greenlet on Windows
"""
import logging
from typing import Optional, Generator, AsyncGenerator
from contextlib import contextmanager, asynccontextmanager

from sqlalchemy import create_engine, text as sql_text
from sqlalchemy.engine import Engine

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker


class DatabaseManager:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.logger = logging.getLogger(__name__)
        # Engines / sessions
        self.sync_engine: Optional[Engine] = None
        self.sync_session_factory: Optional[sessionmaker] = None
        self.async_engine: Optional[AsyncEngine] = None
        self.async_session_factory: Optional[async_sessionmaker] = None

    async def initialize(self):
        if self.database_url.startswith("sqlite+aiosqlite") or self.database_url.startswith("postgresql+asyncpg"):
            # Async mode
            self.async_engine = create_async_engine(self.database_url, echo=False)
            self.async_session_factory = async_sessionmaker(self.async_engine, class_=AsyncSession, expire_on_commit=False)
            await self._test_async()
            self.logger.info("Database initialized (async)")
        else:
            # Sync mode
            self.sync_engine = create_engine(self.database_url, echo=False, future=True)
            self.sync_session_factory = sessionmaker(self.sync_engine, expire_on_commit=False)
            self._test_sync()
            self.logger.info("Database initialized (sync)")

    def _test_sync(self):
        assert self.sync_engine is not None
        with self.sync_engine.connect() as conn:
            conn.execute(sql_text("SELECT 1"))

    async def _test_async(self):
        assert self.async_engine is not None
        async with self.async_engine.begin() as conn:
            await conn.execute(sql_text("SELECT 1"))

    @contextmanager
    def get_sync_session(self):
        if not self.sync_session_factory:
            raise RuntimeError("Sync session factory not initialized")
        session = self.sync_session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        if self.async_session_factory:
            async with self.async_session_factory() as session:
                try:
                    yield session
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise
        elif self.sync_session_factory:
            # Fallback: wrap sync in async context for callers
            # (handlers/services nie używają DB na tym etapie, więc to bezpieczne)
            class _DummyAsyncSession:
                def __init__(self, s):
                    self._s = s
                async def __aenter__(self):
                    return self._s
                async def __aexit__(self, exc_type, exc, tb):
                    pass
            with self.get_sync_session() as s:
                yield s  # type: ignore
        else:
            raise RuntimeError("Database not initialized")

    async def close(self):
        if self.async_engine:
            await self.async_engine.dispose()
        if self.sync_engine:
            self.sync_engine.dispose()
        self.logger.info("Database closed")
