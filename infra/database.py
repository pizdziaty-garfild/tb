# -*- coding: utf-8 -*-
"""
Database Manager - Async SQLAlchemy + Alembic (SQLite dev by default)
"""
import logging
from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import text


class DatabaseManager:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.logger = logging.getLogger(__name__)
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[async_sessionmaker] = None

    async def initialize(self):
        pool_kwargs = {}
        if 'sqlite' in self.database_url.lower():
            pool_kwargs = {
                'poolclass': StaticPool,
                'connect_args': {'check_same_thread': False, 'timeout': 30}
            }
        self.engine = create_async_engine(self.database_url, echo=False, **pool_kwargs)
        self.session_factory = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        await self._test_connection()
        self.logger.info("Database initialized")

    async def _test_connection(self):
        assert self.engine is not None
        async with self.engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            _ = result.scalar()

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        if not self.session_factory:
            raise RuntimeError("Database not initialized")
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def close(self):
        if self.engine:
            await self.engine.dispose()
            self.logger.info("Database closed")
