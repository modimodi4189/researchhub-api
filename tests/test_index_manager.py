"""Focused tests for FAISS index lifecycle helpers."""

import numpy as np

from app.ml import index_manager
from app.ml.faiss_index import create_index


def _patch_in_memory_indexes(monkeypatch):
    user_indexes = {}
    public_index = create_index(dimension=2)
    public_meta = {}

    embeddings = {
        "old text": np.array([10.0, 10.0], dtype="float32"),
        "new text": np.array([0.0, 0.0], dtype="float32"),
        "public text": np.array([1.0, 1.0], dtype="float32"),
        "private text": np.array([2.0, 2.0], dtype="float32"),
        "moved text": np.array([3.0, 3.0], dtype="float32"),
        "query new": np.array([0.0, 0.0], dtype="float32"),
        "query public": np.array([1.0, 1.0], dtype="float32"),
        "query private": np.array([2.0, 2.0], dtype="float32"),
        "query moved": np.array([3.0, 3.0], dtype="float32"),
    }

    def get_user_index(owner_id):
        if owner_id not in user_indexes:
            user_indexes[owner_id] = (create_index(dimension=2), {})
        return user_indexes[owner_id]

    monkeypatch.setattr(
        index_manager,
        "generate_embedding",
        lambda text: embeddings[text],
    )
    monkeypatch.setattr(index_manager, "_get_or_create_user_index", get_user_index)
    monkeypatch.setattr(index_manager, "_get_public_index", lambda: (public_index, public_meta))
    monkeypatch.setattr(index_manager, "_save_user_index", lambda *args: None)
    monkeypatch.setattr(index_manager, "_save_public_index", lambda *args: None)

    return user_indexes, public_index, public_meta


def test_update_paper_in_index_replaces_existing_vectors(monkeypatch):
    user_indexes, public_index, public_meta = _patch_in_memory_indexes(monkeypatch)

    index_manager.update_paper_in_index(10, "old text", 7, True)
    index_manager.update_paper_in_index(10, "new text", 7, True)

    user_index, user_meta = user_indexes[7]
    user_distances, user_ids = index_manager.search_user_papers(7, "query new", k=5)
    public_distances, public_ids = index_manager.search_public_papers("query new", k=5)

    assert user_index.ntotal == 1
    assert public_index.ntotal == 1
    assert user_ids == [10]
    assert public_ids == [10]
    assert user_distances == [0.0]
    assert public_distances == [0.0]
    assert user_meta[10]["text"] == "new text"
    assert public_meta[10]["text"] == "new text"


def test_update_paper_in_index_removes_public_entry_when_private(monkeypatch):
    user_indexes, public_index, public_meta = _patch_in_memory_indexes(monkeypatch)

    index_manager.update_paper_in_index(10, "public text", 7, True)
    index_manager.update_paper_in_index(10, "private text", 7, False, previous_owner_id=7)

    user_index, user_meta = user_indexes[7]
    _, user_ids = index_manager.search_user_papers(7, "query private", k=5)
    public_distances, public_ids = index_manager.search_public_papers("query public", k=5)

    assert user_index.ntotal == 1
    assert public_index.ntotal == 0
    assert user_ids == [10]
    assert public_distances == []
    assert public_ids == []
    assert user_meta[10]["text"] == "private text"
    assert 10 not in public_meta


def test_update_paper_in_index_moves_between_user_indexes(monkeypatch):
    user_indexes, _, _ = _patch_in_memory_indexes(monkeypatch)

    index_manager.update_paper_in_index(10, "private text", 7, False)
    index_manager.update_paper_in_index(
        10,
        "moved text",
        8,
        False,
        previous_owner_id=7,
    )

    old_owner_index, old_owner_meta = user_indexes[7]
    new_owner_index, new_owner_meta = user_indexes[8]
    old_distances, old_ids = index_manager.search_user_papers(7, "query moved", k=5)
    new_distances, new_ids = index_manager.search_user_papers(8, "query moved", k=5)

    assert old_owner_index.ntotal == 0
    assert old_owner_meta == {}
    assert old_distances == []
    assert old_ids == []
    assert new_owner_index.ntotal == 1
    assert new_ids == [10]
    assert new_distances == [0.0]
    assert new_owner_meta[10]["text"] == "moved text"
