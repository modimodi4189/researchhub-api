"""
Tests for /api/v1/search/* endpoints.

The FAISS index functions are mocked in conftest.py (_mock_ml fixture) so
these tests verify the HTTP layer, DB lookup, result shaping, and ordering —
not the vector search itself.
"""

import pytest


# ---------------------------------------------------------------------------
# Search my papers
# ---------------------------------------------------------------------------

async def test_search_my_returns_empty_when_no_index_results(auth_client, created_paper):
    """With the FAISS mock returning empty, search/my returns an empty PaginationResponse."""
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
    # Search results use PaperListResponse — no content field
    assert "content" not in data["items"][0]


async def test_search_my_preserves_relevance_order(auth_client, monkeypatch):
    """
    Results should come back in the order FAISS returned them (relevance order),
    not in database storage order.
    """
    client, _ = auth_client

    # Create two papers
    r1 = await client.post(
        "/api/v1/papers",
        json={"title": "Paper A", "abstract": "First paper", "is_public": True},
    )
    r2 = await client.post(
        "/api/v1/papers",
        json={"title": "Paper B", "abstract": "Second paper", "is_public": True},
    )
    id_a = r1.json()["id"]
    id_b = r2.json()["id"]

    # FAISS returns B first (more relevant), then A
    monkeypatch.setattr(
        "app.api.v1.search.router.search_user_papers_idx",
        lambda user_id, query, k: ([], [id_b, id_a]),
    )

    r = await client.get("/api/v1/search/my?q=test&k=5")
    assert r.status_code == 200
    ids = [item["id"] for item in r.json()["items"]]
    assert ids == [id_b, id_a], "Results must preserve FAISS relevance order"


async def test_search_my_filters_index_hits_to_current_owner(auth_client, client, monkeypatch):
    client, tokens = auth_client
    owned = await client.post(
        "/api/v1/papers",
        json={"title": "Owned Paper", "abstract": "Owned abstract", "is_public": True},
    )
    owned_id = owned.json()["id"]

    other_creds = {"email": "search-owner@example.com", "password": "ownerpass123"}
    await client.post("/api/v1/auth/register", json=other_creds)
    login = await client.post("/api/v1/auth/login", json=other_creds)
    client.headers["Authorization"] = f"Bearer {login.json()['access_token']}"
    other = await client.post(
        "/api/v1/papers",
        json={"title": "Other Paper", "abstract": "Other abstract", "is_public": True},
    )
    other_id = other.json()["id"]

    client.headers["Authorization"] = f"Bearer {tokens['access_token']}"
    monkeypatch.setattr(
        "app.api.v1.search.router.search_user_papers_idx",
        lambda user_id, query, k: ([], [other_id, owned_id]),
    )

    r = await client.get("/api/v1/search/my?q=test&k=5")

    assert r.status_code == 200
    assert [item["id"] for item in r.json()["items"]] == [owned_id]


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


async def test_search_public_filters_stale_private_index_ids(auth_client, monkeypatch):
    client, _ = auth_client
    public_response = await client.post(
        "/api/v1/papers",
        json={"title": "Public Paper", "abstract": "Public abstract", "is_public": True},
    )
    private_response = await client.post(
        "/api/v1/papers",
        json={"title": "Private Paper", "abstract": "Private abstract", "is_public": False},
    )
    public_id = public_response.json()["id"]
    private_id = private_response.json()["id"]

    monkeypatch.setattr(
        "app.api.v1.search.router.search_public_papers_idx",
        lambda query, k: ([], [private_id, public_id]),
    )

    r = await client.get("/api/v1/search/public?q=paper&k=5")

    assert r.status_code == 200
    assert [item["id"] for item in r.json()["items"]] == [public_id]


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

    # Index returns the source paper as the only result
    monkeypatch.setattr(
        "app.api.v1.search.router.search_public_papers_idx",
        lambda query, k: ([], [paper_id]),
    )

    r = await client.get(f"/api/v1/search/similar/{paper_id}?k=3")
    assert r.status_code == 200
    ids = [p["id"] for p in r.json()["items"]]
    assert paper_id not in ids


async def test_similar_filters_private_stale_public_hits(auth_client, client, created_paper, monkeypatch):
    client, tokens = auth_client
    source_id = created_paper["id"]

    other_creds = {"email": "similar-private@example.com", "password": "similarpass123"}
    await client.post("/api/v1/auth/register", json=other_creds)
    login = await client.post("/api/v1/auth/login", json=other_creds)
    client.headers["Authorization"] = f"Bearer {login.json()['access_token']}"
    private_response = await client.post(
        "/api/v1/papers",
        json={"title": "Private Similar", "abstract": "Private abstract", "is_public": False},
    )
    private_id = private_response.json()["id"]

    client.headers["Authorization"] = f"Bearer {tokens['access_token']}"
    monkeypatch.setattr(
        "app.api.v1.search.router.search_public_papers_idx",
        lambda query, k: ([], [source_id, private_id]),
    )

    r = await client.get(f"/api/v1/search/similar/{source_id}?k=3")

    assert r.status_code == 200
    assert r.json()["items"] == []


async def test_similar_requires_auth(client, auth_client, created_paper):
    client.headers.pop("Authorization", None)
    r = await client.get(f"/api/v1/search/similar/{created_paper['id']}")
    assert r.status_code == 403
