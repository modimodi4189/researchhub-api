"""
Tests for /api/v1/search/* endpoints.

The FAISS index functions are mocked in conftest.py (_mock_ml fixture) so
these tests verify the HTTP layer, DB lookup, and result shaping — not the
vector search itself. The index behaviour is exercised separately in the
unit tests for index_manager.
"""

import pytest


# ---------------------------------------------------------------------------
# Search my papers
# ---------------------------------------------------------------------------

async def test_search_my_returns_empty_when_no_index_results(auth_client, created_paper):
    """
    With the FAISS mock returning empty, search/my should return an empty
    PaginationResponse rather than an error.
    """
    client, _ = auth_client
    r = await client.get("/api/v1/search/my?q=neural+networks&k=5")
    assert r.status_code == 200
    data = r.json()
    assert data["items"] == []
    assert data["total"] == 0


async def test_search_my_requires_auth(client):
    r = await client.get("/api/v1/search/my?q=test")
    assert r.status_code == 403


async def test_search_my_requires_query(auth_client):
    client, _ = auth_client
    r = await client.get("/api/v1/search/my")
    assert r.status_code == 422


async def test_search_my_returns_papers_when_index_hits(auth_client, created_paper, monkeypatch):
    """Override the mock to return a real paper ID and verify DB lookup works."""
    client, _ = auth_client
    paper_id = created_paper["id"]

    monkeypatch.setattr(
        "app.api.v1.search.router.search_user_papers_idx",
        lambda user_id, query, k: ([], [paper_id]),
    )

    r = await client.get("/api/v1/search/my?q=neural+networks&k=5")
    assert r.status_code == 200
    data = r.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == paper_id


# ---------------------------------------------------------------------------
# Search public papers
# ---------------------------------------------------------------------------

async def test_search_public_returns_empty_when_no_index_results(auth_client):
    client, _ = auth_client
    r = await client.get("/api/v1/search/public?q=biology&k=5")
    assert r.status_code == 200
    assert r.json()["items"] == []


async def test_search_public_returns_papers_when_index_hits(auth_client, created_paper, monkeypatch):
    client, _ = auth_client
    paper_id = created_paper["id"]

    monkeypatch.setattr(
        "app.api.v1.search.router.search_public_papers_idx",
        lambda query, k: ([], [paper_id]),
    )

    r = await client.get("/api/v1/search/public?q=neural+networks&k=5")
    assert r.status_code == 200
    assert r.json()["items"][0]["id"] == paper_id


async def test_search_public_requires_auth(client):
    r = await client.get("/api/v1/search/public?q=test")
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Similar papers
# ---------------------------------------------------------------------------

async def test_similar_paper_not_found(auth_client):
    client, _ = auth_client
    r = await client.get("/api/v1/search/similar/999999")
    assert r.status_code == 404


async def test_similar_returns_empty_when_no_index_results(auth_client, created_paper):
    client, _ = auth_client
    r = await client.get(f"/api/v1/search/similar/{created_paper['id']}?k=3")
    assert r.status_code == 200
    assert r.json()["items"] == []


async def test_similar_excludes_source_paper(auth_client, created_paper, monkeypatch):
    """
    The source paper must never appear in its own similarity results even if
    the index returns it as the top hit.
    """
    client, _ = auth_client
    paper_id = created_paper["id"]

    # Index returns the source paper as the only result.
    monkeypatch.setattr(
        "app.api.v1.search.router.search_public_papers_idx",
        lambda query, k: ([], [paper_id]),
    )

    r = await client.get(f"/api/v1/search/similar/{paper_id}?k=3")
    assert r.status_code == 200
    ids = [p["id"] for p in r.json()["items"]]
    assert paper_id not in ids


async def test_similar_requires_auth(client, auth_client, created_paper):
    # Reset auth header
    client.headers.pop("Authorization", None)
    r = await client.get(f"/api/v1/search/similar/{created_paper['id']}")
    assert r.status_code == 403
