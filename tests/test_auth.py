"""Tests for /api/v1/auth/* endpoints."""

from contextlib import contextmanager

import pytest

from app.core.limiter import limiter
from app.main import app

CREDS = {"email": "auth_test@example.com", "password": "securepass123"}


def _reset_limiter_state():
    reset = getattr(limiter, "reset", None)
    if reset is not None:
        reset()
        return

    storage = getattr(limiter, "_storage", None)
    if storage is None:
        rate_limiter = getattr(limiter, "_limiter", None)
        storage = getattr(rate_limiter, "storage", None)

    if storage is not None:
        storage.reset()


@pytest.fixture
def enable_rate_limiter():
    @contextmanager
    def _enabled():
        was_enabled = limiter.enabled
        _reset_limiter_state()
        limiter.enabled = True
        try:
            yield
        finally:
            limiter.enabled = was_enabled
            _reset_limiter_state()

    return _enabled


def test_app_uses_shared_limiter_instance():
    assert app.state.limiter is limiter


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------

async def test_register_success(client):
    r = await client.post("/api/v1/auth/register", json=CREDS)
    assert r.status_code == 201
    data = r.json()
    assert data["email"] == CREDS["email"]
    assert "id" in data
    assert "created_at" in data
    assert "hashed_password" not in data


async def test_register_duplicate_email(client):
    await client.post("/api/v1/auth/register", json=CREDS)
    r = await client.post("/api/v1/auth/register", json=CREDS)
    assert r.status_code == 400
    assert "already registered" in r.json()["detail"].lower()


async def test_register_invalid_email(client):
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "validpassword"},
    )
    assert r.status_code == 422


async def test_register_password_too_short(client):
    """Passwords shorter than 8 characters must be rejected at the schema layer."""
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": "shortpass@example.com", "password": "abc123"},
    )
    assert r.status_code == 422


async def test_register_empty_password(client):
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": "empty@example.com", "password": ""},
    )
    assert r.status_code == 422


async def test_register_is_rate_limited(client, enable_rate_limiter):
    with enable_rate_limiter():
        for i in range(10):
            r = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": f"limited-register-{i}@example.com",
                    "password": "securepass123",
                },
            )
            assert r.status_code == 201

        r = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "limited-register-10@example.com",
                "password": "securepass123",
            },
        )
        assert r.status_code == 429


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

async def test_login_success(client):
    await client.post("/api/v1/auth/register", json=CREDS)
    r = await client.post("/api/v1/auth/login", json=CREDS)
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


async def test_login_wrong_password(client):
    await client.post("/api/v1/auth/register", json=CREDS)
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": CREDS["email"], "password": "wrongpassword"},
    )
    assert r.status_code == 401


async def test_login_unknown_email(client):
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "whatever12"},
    )
    assert r.status_code == 401


async def test_login_is_rate_limited(client, enable_rate_limiter):
    with enable_rate_limiter():
        for _ in range(10):
            r = await client.post(
                "/api/v1/auth/login",
                json={"email": "nobody@example.com", "password": "whatever12"},
            )
            assert r.status_code == 401

        r = await client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "whatever12"},
        )
        assert r.status_code == 429


# ---------------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------------

async def test_refresh_with_refresh_token_succeeds(client):
    await client.post("/api/v1/auth/register", json=CREDS)
    login_r = await client.post("/api/v1/auth/login", json=CREDS)
    refresh_token = login_r.json()["refresh_token"]

    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert r.status_code == 200
    data = r.json()
    # Both tokens are rotated on every refresh
    assert "access_token" in data
    assert "refresh_token" in data


async def test_refresh_rejects_reused_refresh_token(client):
    await client.post("/api/v1/auth/register", json=CREDS)
    login_r = await client.post("/api/v1/auth/login", json=CREDS)
    old_refresh_token = login_r.json()["refresh_token"]

    first_refresh = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh_token},
    )
    assert first_refresh.status_code == 200

    reused_refresh = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh_token},
    )
    assert reused_refresh.status_code == 401


async def test_refresh_with_access_token_rejected(client):
    """An access token must not be accepted by the refresh endpoint."""
    await client.post("/api/v1/auth/register", json=CREDS)
    login_r = await client.post("/api/v1/auth/login", json=CREDS)
    access_token = login_r.json()["access_token"]

    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})
    assert r.status_code == 401


async def test_refresh_with_garbage_token_rejected(client):
    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": "not.a.token"})
    assert r.status_code == 401


async def test_refresh_is_rate_limited(client, enable_rate_limiter):
    await client.post("/api/v1/auth/register", json=CREDS)
    login_r = await client.post("/api/v1/auth/login", json=CREDS)
    refresh_token = login_r.json()["refresh_token"]

    with enable_rate_limiter():
        for _ in range(20):
            r = await client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": refresh_token},
            )
            assert r.status_code == 200
            refresh_token = r.json()["refresh_token"]

        r = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert r.status_code == 429


# ---------------------------------------------------------------------------
# Protected endpoint without token
# ---------------------------------------------------------------------------

async def test_protected_endpoint_no_token(client):
    r = await client.get("/api/v1/papers")
    assert r.status_code == 401


async def test_protected_endpoint_malformed_token(client):
    r = await client.get(
        "/api/v1/papers",
        headers={"Authorization": "Bearer thisisnotavalidtoken"},
    )
    assert r.status_code == 401
