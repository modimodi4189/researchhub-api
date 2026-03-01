import faiss
import numpy as np
import pickle
from pathlib import Path

INDEX_DIR = Path("ml_artifacts")
INDEX_DIR.mkdir(exist_ok=True)

PUBLIC_INDEX_PATH = INDEX_DIR / "public_index.faiss"
PUBLIC_META_PATH = INDEX_DIR / "public_meta.pkl"


def create_index(dimension: int = 384) -> faiss.Index:
    return faiss.IndexFlatL2(dimension)


def add_to_index(index: faiss.Index, embedding: np.ndarray):
    embedding = embedding.reshape(1, -1).astype('float32')
    index.add(embedding)
    return index


def search_index(index: faiss.Index, query_embedding: np.ndarray, k: int = 5):
    query_embedding = query_embedding.reshape(1, -1).astype('float32')
    distances, indices = index.search(query_embedding, k)
    return distances[0], indices[0]


def save_index(index: faiss.Index, metadata: dict, index_path: str, meta_path: str):
    faiss.write_index(index, index_path)
    with open(meta_path, 'wb') as f:
        pickle.dump(metadata, f)


def load_index(index_path: str, meta_path: str):
    if not Path(index_path).exists():
        return None, {}
    index = faiss.read_index(index_path)
    with open(meta_path, 'rb') as f:
        metadata = pickle.load(f)
    return index, metadata
