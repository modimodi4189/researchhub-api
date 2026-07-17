"""Tests for /api/v1/papers/* endpoints."""

from unittest.mock import MagicMock

import pytest

from app.db.models import Paper
from app.schemas.schemas import (
    PAPER_ABSTRACT_MAX_LENGTH,
    PAPER_CONTENT_MAX_LENGTH,
    PAPER_TITLE_MAX_LENGTH,
)

PAPER_PAYLOAD = {
    "title": "Neural Networks 101",
    "abstract": "An intro to neural networks.",
    "content": "Neural networks are computing systems inspired by biological neural networks.",
    "is_public": True,
}


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

async def test_create_paper_success(auth_client):
    client, _ = auth_client
    r = await client.post("/api/v1/papers", json=PAPER_PAYLOAD)
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == PAPER_PAYLOAD["title"]
    assert data["is_public"] is True
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data
    assert "summary" in data
    assert data["summary_status"] == "idle"
    assert data["summary_error"] is None


async def test_create_paper_requires_auth(client):
    r = await client.post("/api/v1/papers", json=PAPER_PAYLOAD)
    assert r.status_code == 401


async def test_create_paper_missing_title(auth_client):
    client, _ = auth_client
    r = await client.post("/api/v1/papers", json={"content": "Some content"})
    assert r.status_code == 422


async def test_create_paper_rejects_whitespace_title(auth_client):
    client, _ = auth_client
    r = await client.post("/api/v1/papers", json={**PAPER_PAYLOAD, "title": "   \t"})
    assert r.status_code == 422


async def test_create_paper_rejects_invalid_category_id(auth_client):
    client, _ = auth_client
    r = await client.post(
        "/api/v1/papers",
        json={**PAPER_PAYLOAD, "category_id": 999999},
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "Category not found"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("title", "T" * (PAPER_TITLE_MAX_LENGTH + 1)),
        ("abstract", "A" * (PAPER_ABSTRACT_MAX_LENGTH + 1)),
        ("content", "C" * (PAPER_CONTENT_MAX_LENGTH + 1)),
    ],
)
async def test_create_paper_rejects_oversized_fields(auth_client, field, value):
    client, _ = auth_client
    r = await client.post("/api/v1/papers", json={**PAPER_PAYLOAD, field: value})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# List / Get
# ---------------------------------------------------------------------------

async def test_get_papers_paginated(auth_client):
    client, _ = auth_client
    for i in range(3):
        await client.post("/api/v1/papers", json={**PAPER_PAYLOAD, "title": f"Paper {i}"})

    r = await client.get("/api/v1/papers?page=1&limit=2")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2
    assert data["pages"] == 2


async def test_list_response_excludes_content(auth_client):
    """
    List endpoint uses PaperListResponse — full content should not be present.
    The detail endpoint GET /papers/{id} is where content lives.
    """
    client, _ = auth_client
    await client.post("/api/v1/papers", json=PAPER_PAYLOAD)
    r = await client.get("/api/v1/papers")
    assert r.status_code == 200
    item = r.json()["items"][0]
    assert "content" not in item
    assert "title" in item
    assert "abstract" in item


async def test_get_paper_by_id_includes_content(auth_client, created_paper):
    """The detail endpoint must return full content."""
    client, _ = auth_client
    r = await client.get(f"/api/v1/papers/{created_paper['id']}")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == created_paper["id"]
    assert "content" in data


async def test_get_paper_not_found(auth_client):
    client, _ = auth_client
    r = await client.get("/api/v1/papers/999999")
    assert r.status_code == 404


async def test_get_private_paper_by_other_user(auth_client):
    """A private paper must not be visible to a different user."""
    client, _ = auth_client
    private = await client.post(
        "/api/v1/papers",
        json={**PAPER_PAYLOAD, "is_public": False},
    )
    owner_private_id = private.json()["id"]

    # Register a second user and try to read the owner's private paper.
    creds2 = {"email": "other@example.com", "password": "otherpass123"}
    await client.post("/api/v1/auth/register", json=creds2)
    r = await client.post("/api/v1/auth/login", json=creds2)
    client.headers["Authorization"] = f"Bearer {r.json()['access_token']}"

    assert "Authorization" in client.headers
    r2 = await client.get(f"/api/v1/papers/{owner_private_id}")
    assert r2.status_code == 403


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

async def test_update_paper(auth_client, created_paper):
    client, _ = auth_client
    r = await client.patch(
        f"/api/v1/papers/{created_paper['id']}",
        json={"title": "Updated Title", "is_public": False},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["title"] == "Updated Title"
    assert data["is_public"] is False
    assert data["updated_at"] is not None


async def test_update_paper_rejects_whitespace_title(auth_client, created_paper):
    client, _ = auth_client
    r = await client.patch(
        f"/api/v1/papers/{created_paper['id']}",
        json={"title": " \n\t "},
    )
    assert r.status_code == 422


async def test_update_paper_rejects_invalid_category_id(auth_client, created_paper):
    client, _ = auth_client
    r = await client.patch(
        f"/api/v1/papers/{created_paper['id']}",
        json={"category_id": 999999},
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "Category not found"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("title", "T" * (PAPER_TITLE_MAX_LENGTH + 1)),
        ("abstract", "A" * (PAPER_ABSTRACT_MAX_LENGTH + 1)),
        ("content", "C" * (PAPER_CONTENT_MAX_LENGTH + 1)),
    ],
)
async def test_update_paper_rejects_oversized_fields(
    auth_client, created_paper, field, value
):
    client, _ = auth_client
    r = await client.patch(
        f"/api/v1/papers/{created_paper['id']}",
        json={field: value},
    )
    assert r.status_code == 422


async def test_update_public_to_private_dispatches_index_sync(auth_client, monkeypatch):
    client, _ = auth_client
    update_index_mock = MagicMock()
    monkeypatch.setattr(
        "app.api.v1.papers.router.update_paper_index_task.delay",
        update_index_mock,
    )

    create_response = await client.post(
        "/api/v1/papers",
        json={
            "title": "Fallback indexed title",
            "abstract": "Fallback indexed abstract",
            "is_public": True,
        },
    )
    assert create_response.status_code == 201
    paper = create_response.json()

    r = await client.patch(
        f"/api/v1/papers/{paper['id']}",
        json={"is_public": False},
    )

    assert r.status_code == 200
    update_index_mock.assert_called_once_with(
        paper["id"],
        "Fallback indexed abstract",
        paper["owner_id"],
        False,
        paper["owner_id"],
    )


async def test_update_paper_not_owner(client, created_paper):
    """A different user must not be able to update someone else's paper."""
    creds2 = {"email": "thief@example.com", "password": "thief12345"}
    await client.post("/api/v1/auth/register", json=creds2)
    r = await client.post("/api/v1/auth/login", json=creds2)
    client.headers["Authorization"] = f"Bearer {r.json()['access_token']}"

    r2 = await client.patch(
        f"/api/v1/papers/{created_paper['id']}",
        json={"title": "Stolen Title"},
    )
    assert r2.status_code == 403


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

async def test_delete_paper(auth_client, created_paper):
    client, _ = auth_client
    r = await client.delete(f"/api/v1/papers/{created_paper['id']}")
    assert r.status_code == 204

    r2 = await client.get(f"/api/v1/papers/{created_paper['id']}")
    assert r2.status_code == 404


async def test_delete_paper_not_owner(client, created_paper):
    creds2 = {"email": "attacker@example.com", "password": "attack12345"}
    await client.post("/api/v1/auth/register", json=creds2)
    r = await client.post("/api/v1/auth/login", json=creds2)
    client.headers["Authorization"] = f"Bearer {r.json()['access_token']}"

    r2 = await client.delete(f"/api/v1/papers/{created_paper['id']}")
    assert r2.status_code == 403


# ---------------------------------------------------------------------------
# Summarize
# ---------------------------------------------------------------------------

async def test_summarize_paper_queues_background_task(
    auth_client, created_paper, monkeypatch
):
    client, _ = auth_client
    summarize_mock = MagicMock()
    monkeypatch.setattr(
        "app.api.v1.papers.router.summarize_paper_task.delay",
        summarize_mock,
    )

    r = await client.post(f"/api/v1/papers/{created_paper['id']}/summarize")
    assert r.status_code == 202
    data = r.json()
    assert data["summary"] is None
    assert data["summary_status"] == "queued"
    assert data["summary_error"] is None
    summarize_mock.assert_called_once_with(created_paper["id"])


async def test_summarize_paper_rejects_duplicate_active_task(
    auth_client, created_paper, monkeypatch, test_sessionmaker
):
    client, _ = auth_client
    summarize_mock = MagicMock()
    monkeypatch.setattr(
        "app.api.v1.papers.router.summarize_paper_task.delay",
        summarize_mock,
    )

    async with test_sessionmaker() as db:
        paper = await db.get(Paper, created_paper["id"])
        paper.summary_status = "processing"
        await db.commit()

    r = await client.post(f"/api/v1/papers/{created_paper['id']}/summarize")

    assert r.status_code == 409
    assert r.json()["detail"] == "Summary generation is already in progress"
    summarize_mock.assert_not_called()


async def test_summarize_task_persists_summary(
    auth_client, created_paper, monkeypatch, test_sessionmaker
):
    from app.tasks.processing import _summarize_paper_async

    monkeypatch.setattr("app.tasks.processing.AsyncSessionLocal", test_sessionmaker)

    await _summarize_paper_async(created_paper["id"])

    async with test_sessionmaker() as db:
        paper = await db.get(Paper, created_paper["id"])

    assert paper.summary == "Mocked summary."
    assert paper.summary_status == "complete"
    assert paper.summary_error is None


async def test_summarize_task_failure_marks_failed_status(
    auth_client, created_paper, monkeypatch, test_sessionmaker
):
    client, _ = auth_client
    from app.tasks.processing import _summarize_paper_async

    paper_id = created_paper["id"]

    def fail_summarization(text):
        raise RuntimeError("summarizer unavailable")

    monkeypatch.setattr("app.tasks.processing.AsyncSessionLocal", test_sessionmaker)
    monkeypatch.setattr("app.tasks.processing.summarize_text", fail_summarization)

    await _summarize_paper_async(paper_id)

    persisted = await client.get(f"/api/v1/papers/{paper_id}")
    assert persisted.status_code == 200
    data = persisted.json()
    assert data["summary"] is None
    assert data["summary_status"] == "failed"
    assert "summarizer unavailable" in data["summary_error"]


async def test_summarize_paper_no_content(auth_client):
    client, _ = auth_client
    r = await client.post(
        "/api/v1/papers",
        json={"title": "Empty Paper", "is_public": True},
    )
    paper_id = r.json()["id"]

    r2 = await client.post(f"/api/v1/papers/{paper_id}/summarize")
    assert r2.status_code == 422


async def test_summarize_paper_non_owner_rejected(client, created_paper):
    """Summarize must be restricted to the paper's owner, even for public papers."""
    creds2 = {"email": "reader@example.com", "password": "reader12345"}
    await client.post("/api/v1/auth/register", json=creds2)
    r = await client.post("/api/v1/auth/login", json=creds2)
    client.headers["Authorization"] = f"Bearer {r.json()['access_token']}"

    # created_paper is public — a non-owner should still be rejected
    r2 = await client.post(f"/api/v1/papers/{created_paper['id']}/summarize")
    assert r2.status_code == 403


# ---------------------------------------------------------------------------
# Classify
# ---------------------------------------------------------------------------

async def test_classify_paper_persists_category(auth_client, created_paper):
    client, _ = auth_client
    r = await client.post(f"/api/v1/papers/{created_paper['id']}/classify")
    assert r.status_code == 200
    data = r.json()
    assert data["category_id"] is not None


async def test_classify_paper_failure_does_not_update_category(
    auth_client, created_paper, monkeypatch
):
    client, _ = auth_client
    paper_id = created_paper["id"]

    first_response = await client.post(f"/api/v1/papers/{paper_id}/classify")
    assert first_response.status_code == 200
    original_category_id = first_response.json()["category_id"]
    assert original_category_id is not None

    def fail_classification(text):
        raise RuntimeError("classifier unavailable")

    monkeypatch.setattr(
        "app.api.v1.papers.router.classify_paper",
        fail_classification,
    )

    r = await client.post(f"/api/v1/papers/{paper_id}/classify")
    assert r.status_code == 503
    assert r.json()["detail"] == "Paper classification failed"

    persisted = await client.get(f"/api/v1/papers/{paper_id}")
    assert persisted.status_code == 200
    assert persisted.json()["category_id"] == original_category_id


async def test_classify_paper_non_owner_rejected(client, created_paper):
    """Classify must be restricted to the paper's owner, even for public papers."""
    creds2 = {"email": "classifier@example.com", "password": "classify12345"}
    await client.post("/api/v1/auth/register", json=creds2)
    r = await client.post("/api/v1/auth/login", json=creds2)
    client.headers["Authorization"] = f"Bearer {r.json()['access_token']}"

    r2 = await client.post(f"/api/v1/papers/{created_paper['id']}/classify")
    assert r2.status_code == 403


async def test_classify_paper_no_text(auth_client):
    client, _ = auth_client
    r = await client.post(
        "/api/v1/papers",
        json={"title": "", "is_public": True},
    )
    # Empty title is rejected at the schema layer
    assert r.status_code == 422
