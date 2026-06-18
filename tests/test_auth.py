"""Tests for /api/v1/auth/* endpoints."""

import pytest

CREDS = {"email": "auth_test@example.com", "password": "securepass123"}


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


# ---------------------------------------------------------------------------
# Protected endpoint without token
# ---------------------------------------------------------------------------

async def test_protected_endpoint_no_token(client):
    r = await client.get("/api/v1/papers")
    assert r.status_code == 403


async def test_protected_endpoint_malformed_token(client):
    r = await client.get(
        "/api/v1/papers",
        headers={"Authorization": "Bearer thisisnotavalidtoken"},
    )
    assert r.status_code == 401
