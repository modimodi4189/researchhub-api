import faiss
import numpy as np
import pickle
from pathlib import Path


def create_index(dimension: int = 384) -> faiss.IndexIDMap:
    """
    Create an IndexIDMap wrapping IndexFlatL2.

    IndexIDMap stores vectors alongside caller-supplied integer IDs (paper_ids).
    This means:
      - add_with_ids() maps paper_id → vector directly.
      - search() returns actual paper_ids in the result, not internal array positions.
      - remove_ids() deletes vectors by paper_id without requiring a full rebuild.
    """
    base_index = faiss.IndexFlatL2(dimension)
    return faiss.IndexIDMap(base_index)


def add_to_index(index: faiss.IndexIDMap, embedding: np.ndarray, paper_id: int) -> None:
    vector = embedding.reshape(1, -1).astype("float32")
    ids = np.array([paper_id], dtype="int64")
    index.add_with_ids(vector, ids)


def remove_from_index(index: faiss.IndexIDMap, paper_id: int) -> None:
    """Remove a vector by its paper_id. Operates in-place."""
    ids = np.array([paper_id], dtype="int64")
    selector = faiss.IDSelectorArray(len(ids), faiss.swig_ptr(ids))
    index.remove_ids(selector)


def search_index(
    index: faiss.IndexIDMap, query_embedding: np.ndarray, k: int = 5
):
    """
    Return (distances, paper_ids) for the k nearest neighbours.
    FAISS returns -1 as a sentinel when fewer than k results exist —
    callers must filter those out.
    """
    query = query_embedding.reshape(1, -1).astype("float32")
    actual_k = min(k, index.ntotal)
    if actual_k == 0:
        return np.array([], dtype="float32"), np.array([], dtype="int64")
    distances, paper_ids = index.search(query, actual_k)
    return distances[0], paper_ids[0]


def save_index(
    index: faiss.IndexIDMap,
    metadata: dict,
    index_path: str,
    meta_path: str,
) -> None:
    faiss.write_index(index, str(index_path))
    with open(meta_path, "wb") as f:
        pickle.dump(metadata, f)


def load_index(index_path: str, meta_path: str):
    """
    Load a saved index and its metadata.
    Returns (None, {}) if either file is missing — callers should
    create a fresh index in that case.
    """
    index_p = Path(index_path)
    meta_p = Path(meta_path)
    if not index_p.exists() or not meta_p.exists():
        return None, {}
    index = faiss.read_index(str(index_p))
    with open(meta_p, "rb") as f:
        metadata = pickle.load(f)
    return index, metadata
