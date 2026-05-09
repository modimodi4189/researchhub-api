import asyncio
from logging.config import fileConfig

from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

# Import models so Alembic can detect schema changes via autogenerate.
from app.db.models import Base
from app.core.config import settings

config = context.config
fileConfig(config.config_file_name)

# The metadata Alembic compares against when autogenerating migrations.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations without an active DB connection — emits SQL to stdout.
    Useful for reviewing what will be executed before running it.
    """
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Create an async engine and run migrations via run_sync so Alembic's
    synchronous migration API can work over an asyncpg connection.
    """
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
