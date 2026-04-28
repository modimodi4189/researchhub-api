import numpy as np
from pathlib import Path

from app.core.config import settings
from app.ml.faiss_index import (
    create_index,
    add_to_index,
    remove_from_index,
    search_index,
    save_index,
    load_index,
)
from app.ml.embeddings import generate_embedding

INDEX_DIR = Path(settings.FAISS_INDEX_DIR)
INDEX_DIR.mkdir(parents=True, exist_ok=True)

USER_INDEX_DIR = INDEX_DIR / "user_indices"
USER_INDEX_DIR.mkdir(parents=True, exist_ok=True)

PUBLIC_INDEX_PATH = INDEX_DIR / "public_index.faiss"
PUBLIC_META_PATH = INDEX_DIR / "public_meta.pkl"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user_index_path(user_id: int) -> Path:
    return USER_INDEX_DIR / f"user_{user_id}.faiss"


def _user_meta_path(user_id: int) -> Path:
    return USER_INDEX_DIR / f"user_{user_id}_meta.pkl"


def _get_or_create_user_index(user_id: int):
    index, metadata = load_index(
        str(_user_index_path(user_id)),
        str(_user_meta_path(user_id)),
    )
    if index is None:
        index = create_index(dimension=384)
        metadata = {}
    return index, metadata


def _save_user_index(user_id: int, index, metadata: dict) -> None:
    save_index(index, metadata, str(_user_index_path(user_id)), str(_user_meta_path(user_id)))


def _get_public_index():
    index, metadata = load_index(str(PUBLIC_INDEX_PATH), str(PUBLIC_META_PATH))
    if index is None:
        index = create_index(dimension=384)
        metadata = {}
    return index, metadata


def _save_public_index(index, metadata: dict) -> None:
    save_index(index, metadata, str(PUBLIC_INDEX_PATH), str(PUBLIC_META_PATH))


def _filter_results(distances, paper_ids):
    """Strip FAISS sentinel values (-1) returned when k > index.ntotal."""
    valid = [(d, pid) for d, pid in zip(distances, paper_ids) if pid != -1]
    if not valid:
        return [], []
    dist_out, ids_out = zip(*valid)
    return list(dist_out), list(ids_out)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def add_paper_to_index(paper_id: int, text: str, owner_id: int, is_public: bool) -> None:
    embedding = generate_embedding(text)

    user_index, user_meta = _get_or_create_user_index(owner_id)
    add_to_index(user_index, embedding, paper_id)
    user_meta[paper_id] = {"text": text[:500]}
    _save_user_index(owner_id, user_index, user_meta)

    if is_public:
        public_index, public_meta = _get_public_index()
        add_to_index(public_index, embedding, paper_id)
        public_meta[paper_id] = {"text": text[:500], "owner_id": owner_id}
        _save_public_index(public_index, public_meta)


def remove_paper_from_index(paper_id: int, owner_id: int, is_public: bool) -> None:
    user_index, user_meta = _get_or_create_user_index(owner_id)
    if paper_id in user_meta:
        remove_from_index(user_index, paper_id)
        del user_meta[paper_id]
        _save_user_index(owner_id, user_index, user_meta)

    if is_public:
        public_index, public_meta = _get_public_index()
        if paper_id in public_meta:
            remove_from_index(public_index, paper_id)
            del public_meta[paper_id]
            _save_public_index(public_index, public_meta)


def search_user_papers(user_id: int, query: str, k: int = 5):
    index, _ = _get_or_create_user_index(user_id)
    if index.ntotal == 0:
        return [], []
    query_embedding = generate_embedding(query)
    distances, paper_ids = search_index(index, query_embedding, k)
    return _filter_results(distances, paper_ids)


def search_public_papers(query: str, k: int = 5):
    index, _ = _get_public_index()
    if index.ntotal == 0:
        return [], []
    query_embedding = generate_embedding(query)
    distances, paper_ids = search_index(index, query_embedding, k)
    return _filter_results(distances, paper_ids)
