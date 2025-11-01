# -*- coding: utf-8 -*-
"""
Database Manager - dual-mode (sync/async) with safe sync initialize (no test query)
"""
import logging
from typing import Optional, AsyncGenerator
from contextlib import contextmanager, asynccontextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy import text as sql_text

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker


class DatabaseManager:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.logger = logging.getLogger(__name__)
        self.sync_engine: Optional[Engine] = None
        self.sync_session_factory: Optional[sessionmaker] = None
        self.async_engine: Optional[AsyncEngine] = None
        self.async_session_factory: Optional[async_sessionmaker] = None
        self._mode = "unknown"

    async def initialize(self):
        if self.database_url.startswith(("sqlite+aiosqlite", "postgresql+asyncpg")):
            # Async mode
            self._mode = "async"
            self.async_engine = create_async_engine(self.database_url, echo=False)
            self.async_session_factory = async_sessionmaker(self.async_engine, class_=AsyncSession, expire_on_commit=False)
            # Light async connectivity check
            try:
                async with self.async_engine.begin() as conn:
                    await conn.execute(sql_text("SELECT 1"))
            except Exception as e:
                self.logger.warning(f"Async DB connectivity check failed: {e}")
            self.logger.info("Database initialized (async mode)")
        else:
            # Sync mode (no test query to avoid any greenlet paths on Windows)
            self._mode = "sync"
            self.sync_engine = create_engine(self.database_url, echo=False, future=True)
            self.sync_session_factory = sessionmaker(self.sync_engine, expire_on_commit=False)
            self.logger.info("Database initialized (sync mode)")

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
            # Provide a minimal async-compatible wrapper around sync session
            class _AsyncLikeSession:
                def __init__(self, sync_session):
                    self._s = sync_session
                async def execute(self, *args, **kwargs):
                    return self._s.execute(*args, **kwargs)
                async def commit(self):
                    self._s.commit()
                async def rollback(self):
                    self._s.rollback()
                async def close(self):
                    self._s.close()
            with self.get_sync_session() as s:
                yield _AsyncLikeSession(s)  # type: ignore
        else:
            raise RuntimeError("Database not initialized")

    async def close(self):
        if self.async_engine:
            await self.async_engine.dispose()
        if self.sync_engine:
            self.sync_engine.dispose()
        self.logger.info("Database closed")

    @property
    def mode(self) -> str:
        return self._mode
