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
from alembic import command
from alembic.config import Config
from sqlalchemy import text
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
DEFAULT_DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@postgres:5432/researchhub",
)
TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    f"{DEFAULT_DB_URL.rsplit('/', 1)[0]}/test_researchhub",
)
os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["DEBUG"] = "False"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"

from app.main import app  # noqa: E402
from app.db.models import Base  # noqa: E402
from app.core.limiter import limiter  # noqa: E402
from app.db.database import get_db  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class _InMemoryRefreshTokenStore:
    def __init__(self):
        self.tokens = {}

    async def store(self, jti: str, user_id: int) -> None:
        self.tokens[jti] = str(user_id)

    async def consume(self, jti: str, user_id: int) -> bool:
        return self.tokens.pop(jti, None) == str(user_id)

# ---------------------------------------------------------------------------
# Rate limiting — disabled for the entire test session.
#
# The limiter is keyed by source IP. In CI and in local Docker test runs,
# every test request comes from the same IP (127.0.0.1). The auth_client
# fixture calls /auth/register + /auth/login for almost every test in the
# suite, so without this, the real 10/minute limit on those endpoints trips
# partway through the run — causing later tests to receive a 429 instead of
# a token pair, which then fails with KeyError: 'access_token' in this file.
#
# slowapi's Limiter has a global `enabled` switch that bypasses every
# @limiter.limit(...) decorator without needing to mock each one individually.
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True, scope="session")
def _disable_rate_limiting():
    limiter.enabled = False
    yield
    limiter.enabled = True

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


@pytest.fixture
def test_sessionmaker():
    return _TestSession


async def _override_get_db():
    async with _TestSession() as session:
        try:
            yield session
        finally:
            await session.close()


app.dependency_overrides[get_db] = _override_get_db


# ---------------------------------------------------------------------------
# Database lifecycle - run Alembic migrations against a clean test schema.
# ---------------------------------------------------------------------------
def _run_alembic_upgrade(connection) -> None:
    alembic_cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    alembic_cfg.attributes["connection"] = connection
    command.upgrade(alembic_cfg, "head")


async def _reset_public_schema(connection) -> None:
    await connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
    await connection.execute(text("CREATE SCHEMA public"))


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _db_lifecycle():
    async with _test_engine.begin() as conn:
        await _reset_public_schema(conn)
        await conn.run_sync(_run_alembic_upgrade)
    yield
    async with _test_engine.begin() as conn:
        await _reset_public_schema(conn)


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
    monkeypatch.setattr("app.tasks.processing.summarize_paper_task.delay", mock)
    monkeypatch.setattr("app.tasks.processing.update_paper_index_task.delay", mock)
    return mock


# ---------------------------------------------------------------------------
# Mock refresh-token Redis store so auth tests do not need Redis.
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _mock_refresh_token_store(monkeypatch):
    store = _InMemoryRefreshTokenStore()
    monkeypatch.setattr("app.api.v1.auth.router.refresh_token_store", store)
    return store


# ---------------------------------------------------------------------------
# Mock ML inference so no models are loaded and tests run in seconds.
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _mock_ml(monkeypatch):
    monkeypatch.setattr("app.tasks.processing.summarize_text", lambda text: "Mocked summary.")
    monkeypatch.setattr(
        "app.api.v1.papers.router.classify_paper",
        lambda text: {"category": "machine learning", "confidence": 0.95},
    )
    monkeypatch.setattr(
        "app.api.v1.search.router.search_user_papers_idx",
        lambda user_id, query, k=5: ([], []),
    )
    monkeypatch.setattr(
        "app.api.v1.search.router.search_public_papers_idx",
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
