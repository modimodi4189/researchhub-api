"""Tests for /api/v1/collections/* endpoints."""

import pytest

COLLECTION_PAYLOAD = {"name": "My Research"}


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

async def test_create_collection(auth_client):
    client, _ = auth_client
    r = await client.post("/api/v1/collections", json=COLLECTION_PAYLOAD)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == COLLECTION_PAYLOAD["name"]
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


async def test_create_collection_requires_auth(client):
    r = await client.post("/api/v1/collections", json=COLLECTION_PAYLOAD)
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

async def test_list_collections_paginated(auth_client):
    client, _ = auth_client
    for i in range(4):
        await client.post("/api/v1/collections", json={"name": f"Col {i}"})

    r = await client.get("/api/v1/collections?page=1&limit=3")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 4
    assert len(data["items"]) == 3
    assert data["pages"] == 2


# ---------------------------------------------------------------------------
# Get single
# ---------------------------------------------------------------------------

async def test_get_collection_with_papers(auth_client, created_paper):
    client, _ = auth_client
    coll_r = await client.post("/api/v1/collections", json=COLLECTION_PAYLOAD)
    coll_id = coll_r.json()["id"]
    paper_id = created_paper["id"]

    await client.post(f"/api/v1/collections/{coll_id}/papers/{paper_id}")

    r = await client.get(f"/api/v1/collections/{coll_id}")
    assert r.status_code == 200
    data = r.json()
    assert len(data["papers"]) == 1
    assert data["papers"][0]["id"] == paper_id
    # Collection paper list uses PaperListResponse — no content field
    assert "content" not in data["papers"][0]


async def test_get_collection_not_found(auth_client):
    client, _ = auth_client
    r = await client.get("/api/v1/collections/999999")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Update (PATCH)
# ---------------------------------------------------------------------------

async def test_update_collection(auth_client):
    client, _ = auth_client
    coll_r = await client.post("/api/v1/collections", json=COLLECTION_PAYLOAD)
    coll_id = coll_r.json()["id"]

    r = await client.patch(
        f"/api/v1/collections/{coll_id}",
        json={"name": "Updated Name"},
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Updated Name"


async def test_update_collection_empty_body_is_noop(auth_client):
    """PATCH with no fields should return the collection unchanged."""
    client, _ = auth_client
    coll_r = await client.post("/api/v1/collections", json=COLLECTION_PAYLOAD)
    coll_id = coll_r.json()["id"]
    original_name = coll_r.json()["name"]

    r = await client.patch(f"/api/v1/collections/{coll_id}", json={})
    assert r.status_code == 200
    assert r.json()["name"] == original_name


async def test_update_collection_not_owner(client, auth_client):
    owner_client, _ = auth_client
    coll_r = await owner_client.post("/api/v1/collections", json=COLLECTION_PAYLOAD)
    coll_id = coll_r.json()["id"]

    creds2 = {"email": "intruder@example.com", "password": "intruder12345"}
    await client.post("/api/v1/auth/register", json=creds2)
    r = await client.post("/api/v1/auth/login", json=creds2)
    client.headers["Authorization"] = f"Bearer {r.json()['access_token']}"

    r2 = await client.patch(f"/api/v1/collections/{coll_id}", json={"name": "Hijacked"})
    # Other user's collection is invisible to other users — returns 404, not 403
    assert r2.status_code == 404


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

async def test_delete_collection(auth_client):
    client, _ = auth_client
    coll_r = await client.post("/api/v1/collections", json=COLLECTION_PAYLOAD)
    coll_id = coll_r.json()["id"]

    r = await client.delete(f"/api/v1/collections/{coll_id}")
    assert r.status_code == 204

    r2 = await client.get(f"/api/v1/collections/{coll_id}")
    assert r2.status_code == 404


# ---------------------------------------------------------------------------
# Add / Remove papers
# ---------------------------------------------------------------------------

async def test_add_paper_to_collection(auth_client, created_paper):
    client, _ = auth_client
    coll_r = await client.post("/api/v1/collections", json=COLLECTION_PAYLOAD)
    coll_id = coll_r.json()["id"]

    r = await client.post(
        f"/api/v1/collections/{coll_id}/papers/{created_paper['id']}"
    )
    assert r.status_code == 201
    assert r.json()["message"] == "Paper added to collection"


async def test_add_paper_to_collection_idempotent(auth_client, created_paper):
    """Adding the same paper twice must not duplicate it."""
    client, _ = auth_client
    coll_r = await client.post("/api/v1/collections", json=COLLECTION_PAYLOAD)
    coll_id = coll_r.json()["id"]
    paper_id = created_paper["id"]

    await client.post(f"/api/v1/collections/{coll_id}/papers/{paper_id}")
    await client.post(f"/api/v1/collections/{coll_id}/papers/{paper_id}")

    r = await client.get(f"/api/v1/collections/{coll_id}")
    assert len(r.json()["papers"]) == 1


async def test_remove_paper_from_collection(auth_client, created_paper):
    client, _ = auth_client
    coll_r = await client.post("/api/v1/collections", json=COLLECTION_PAYLOAD)
    coll_id = coll_r.json()["id"]
    paper_id = created_paper["id"]

    await client.post(f"/api/v1/collections/{coll_id}/papers/{paper_id}")
    r = await client.delete(f"/api/v1/collections/{coll_id}/papers/{paper_id}")
    assert r.status_code == 204

    r2 = await client.get(f"/api/v1/collections/{coll_id}")
    assert len(r2.json()["papers"]) == 0


async def test_remove_paper_not_in_collection(auth_client, created_paper):
    client, _ = auth_client
    coll_r = await client.post("/api/v1/collections", json=COLLECTION_PAYLOAD)
    coll_id = coll_r.json()["id"]

    r = await client.delete(
        f"/api/v1/collections/{coll_id}/papers/{created_paper['id']}"
    )
    assert r.status_code == 404
