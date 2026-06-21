"""Focused tests for FAISS index lifecycle helpers."""

import numpy as np

from app.ml import index_manager


class FakeIndex:
    def __init__(self):
        self.ids = []

    @property
    def ntotal(self):
        return len(self.ids)


def test_update_paper_in_index_replaces_existing_vectors(monkeypatch):
    user_index = FakeIndex()
    public_index = FakeIndex()
    user_meta = {}
    public_meta = {}

    def fake_add(index, embedding, paper_id):
        index.ids.append(paper_id)

    def fake_remove(index, paper_id):
        index.ids = [existing_id for existing_id in index.ids if existing_id != paper_id]

    monkeypatch.setattr(index_manager, "generate_embedding", lambda text: np.zeros(384))
    monkeypatch.setattr(index_manager, "add_to_index", fake_add)
    monkeypatch.setattr(index_manager, "remove_from_index", fake_remove)
    monkeypatch.setattr(
        index_manager,
        "_get_or_create_user_index",
        lambda owner_id: (user_index, user_meta),
    )
    monkeypatch.setattr(index_manager, "_get_public_index", lambda: (public_index, public_meta))
    monkeypatch.setattr(index_manager, "_save_user_index", lambda *args: None)
    monkeypatch.setattr(index_manager, "_save_public_index", lambda *args: None)

    index_manager.update_paper_in_index(10, "old text", 7, True)
    index_manager.update_paper_in_index(10, "new text", 7, True)

    assert user_index.ids == [10]
    assert public_index.ids == [10]
    assert user_meta[10]["text"] == "new text"
    assert public_meta[10]["text"] == "new text"


def test_update_paper_in_index_removes_public_entry_when_private(monkeypatch):
    user_index = FakeIndex()
    public_index = FakeIndex()
    user_meta = {}
    public_meta = {}

    def fake_add(index, embedding, paper_id):
        index.ids.append(paper_id)

    def fake_remove(index, paper_id):
        index.ids = [existing_id for existing_id in index.ids if existing_id != paper_id]

    monkeypatch.setattr(index_manager, "generate_embedding", lambda text: np.zeros(384))
    monkeypatch.setattr(index_manager, "add_to_index", fake_add)
    monkeypatch.setattr(index_manager, "remove_from_index", fake_remove)
    monkeypatch.setattr(
        index_manager,
        "_get_or_create_user_index",
        lambda owner_id: (user_index, user_meta),
    )
    monkeypatch.setattr(index_manager, "_get_public_index", lambda: (public_index, public_meta))
    monkeypatch.setattr(index_manager, "_save_user_index", lambda *args: None)
    monkeypatch.setattr(index_manager, "_save_public_index", lambda *args: None)

    index_manager.update_paper_in_index(10, "public text", 7, True)
    index_manager.update_paper_in_index(10, "private text", 7, False, previous_owner_id=7)

    assert user_index.ids == [10]
    assert public_index.ids == []
    assert user_meta[10]["text"] == "private text"
    assert 10 not in public_meta
