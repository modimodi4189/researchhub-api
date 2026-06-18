"""
Shared pytest configuration and fixtures.

Requirements:
  - A running PostgreSQL instance. When running inside Docker (recommended):
        docker exec -it researchhub-api-api-1 python -m pytest --tb=short
    The default URL uses the Docker Compose service name 'postgres'.
    Override via TEST_DATABASE_URL env var when running outside Docker.

  - Redis is NOT required — Celery tasks are mocked at the .delay() call site.
  - ML models are NOT loaded — summarize_text and classify_paper are mocked.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# ---------------------------------------------------------------------------
# Ensure logs/ directory exists before the app is imported.
# logging.py adds a Loguru file sink at "logs/app.log" at module level.
# ---------------------------------------------------------------------------
Path("logs").mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Override settings BEFORE any app module is imported so pydantic-settings
# picks up the test values.
# ---------------------------------------------------------------------------
TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@postgres:5432/test_researchhub",
)
os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["DEBUG"] = "False"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"

from app.main import app
from app.db.models import Base
from app.core.limiter import limiter
from app.db.database import get_db

# ---------------------------------------------------------------------------
# Test database engine using NullPool.
#
# NullPool disables connection pooling entirely — every operation opens a
# fresh connection and closes it immediately when done. This is slower than
# pooling but eliminates the asyncpg InterfaceError that occurs when pytest-
# asyncio 0.23.x runs fixtures across different coroutine contexts while a
# pooled connection is still considered "in use" by a previous operation.
# ---------------------------------------------------------------------------
_test_engine = create_async_engine(TEST_DB_URL, echo=False, poolclass=NullPool)
_TestSession = async_sessionmaker(_test_engine, class_=AsyncSession, expire_on_commit=False)


async def _override_get_db():
    async with _TestSession() as session:
        try:
            yield session
        finally:
            await session.close()


app.dependency_overrides[get_db] = _override_get_db


# ---------------------------------------------------------------------------
# Database lifecycle — create all tables once per session, drop after.
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture(scope="session", autouse=True)
async def _db_lifecycle():
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ---------------------------------------------------------------------------
# Database lifecycle — create all tables once per session, drop after.
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture(scope="session", autouse=True)
async def _db_lifecycle():
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ---------------------------------------------------------------------------
# Truncate all user-data tables between tests for full isolation.
# Order matters because of FK constraints.
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture(autouse=True)
async def _clean_db():
    yield
    async with _test_engine.begin() as conn:
        await conn.execute(Base.metadata.tables["paper_collections"].delete())
        for table_name in ("papers", "collections", "categories", "users"):
            await conn.execute(Base.metadata.tables[table_name].delete())


# ---------------------------------------------------------------------------
# Mock Celery .delay() so no broker is needed.
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _mock_celery(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr("app.tasks.processing.process_paper.delay", mock)
    monkeypatch.setattr("app.tasks.processing.remove_paper_from_index_task.delay", mock)
    return mock


# ---------------------------------------------------------------------------
# Mock ML inference so no models are loaded and tests run in seconds.
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _mock_ml(monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.papers.router.summarize_text",
        lambda text: "Mocked summary.",
    )
    monkeypatch.setattr(
        "app.api.v1.papers.router.classify_paper",
        lambda text: {"category": "machine learning", "confidence": 0.95},
    )
    monkeypatch.setattr(
        "app.ml.index_manager.search_user_papers",
        lambda user_id, query, k=5: ([], []),
    )
    monkeypatch.setattr(
        "app.ml.index_manager.search_public_papers",
        lambda query, k=5: ([], []),
    )


# ---------------------------------------------------------------------------
# HTTP client
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def client():
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Authenticated client — registers and logs in a fresh user.
# Returns (client, tokens_dict).
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def auth_client(client):
    creds = {"email": "fixture@example.com", "password": "testpass123"}
    await client.post("/api/v1/auth/register", json=creds)
    r = await client.post("/api/v1/auth/login", json=creds)
    tokens = r.json()
    client.headers["Authorization"] = f"Bearer {tokens['access_token']}"
    return client, tokens


# ---------------------------------------------------------------------------
# A paper already created by the authenticated user.
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def created_paper(auth_client):
    client, _ = auth_client
    r = await client.post(
        "/api/v1/papers",
        json={
            "title": "Test Paper",
            "abstract": "Test abstract.",
            "content": "Machine learning is a branch of artificial intelligence.",
            "is_public": True,
        },
    )
    assert r.status_code == 201
    return r.json()
