# Add missing sync driver for Alembic offline/online runs with aiosqlite URL.
# Alembic uses synchronous engine_from_config; with sqlite+aiosqlite this
# requires greenlet. Easiest fix: switch env.py to use sqlite+pysqlite for
# migrations while keeping app runtime async.

from __future__ import with_statement
from alembic import context
from sqlalchemy import engine_from_config, pool
from logging.config import fileConfig
import os

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Force sync URL for migrations if async driver is set
sync_url = config.get_main_option("sqlalchemy.url").replace("sqlite+aiosqlite", "sqlite+pysqlite")
config.set_main_option("sqlalchemy.url", sync_url)

def run_migrations_offline():
    context.configure(
        url=sync_url,
        target_metadata=None,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = sync_url
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=None)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
