import faiss
import numpy as np
import pickle
from pathlib import Path
from app.ml.faiss_index import create_index
from app.ml.embeddings import generate_embedding

INDEX_DIR = Path("ml_artifacts")
INDEX_DIR.mkdir(exist_ok=True)

USER_INDEX_DIR = INDEX_DIR / "user_indices"
USER_INDEX_DIR.mkdir(exist_ok=True)

PUBLIC_INDEX_PATH = INDEX_DIR / "public_index.faiss"
PUBLIC_META_PATH = INDEX_DIR / "public_meta.pkl"


def get_user_index_path(user_id: int) -> Path:
    return USER_INDEX_DIR / f"user_{user_id}.faiss"


def get_user_meta_path(user_id: int) -> Path:
    return USER_INDEX_DIR / f"user_{user_id}_meta.pkl"


def get_or_create_user_index(user_id: int):
    index_path = get_user_index_path(user_id)
    meta_path = get_user_meta_path(user_id)
    
    if index_path.exists():
        index = faiss.read_index(str(index_path))
        with open(meta_path, 'rb') as f:
            metadata = pickle.load(f)
    else:
        index = create_index(dimension=384)
        metadata = {}
    
    return index, metadata


def save_user_index(user_id: int, index, metadata: dict):
    index_path = get_user_index_path(user_id)
    meta_path = get_user_meta_path(user_id)
    
    faiss.write_index(index, str(index_path))
    with open(meta_path, 'wb') as f:
        pickle.dump(metadata, f)


def get_public_index():
    if PUBLIC_INDEX_PATH.exists():
        index = faiss.read_index(str(PUBLIC_INDEX_PATH))
        with open(PUBLIC_META_PATH, 'rb') as f:
            metadata = pickle.load(f)
    else:
        index = create_index(dimension=384)
        metadata = {}
    return index, metadata


def save_public_index(index, metadata: dict):
    faiss.write_index(index, str(PUBLIC_INDEX_PATH))
    with open(PUBLIC_META_PATH, 'wb') as f:
        pickle.dump(metadata, f)


def search_index(index, query_embedding: np.ndarray, k: int = 5):
    query_embedding = query_embedding.reshape(1, -1).astype('float32')
    distances, indices = index.search(query_embedding, k)
    return distances[0], indices[0]


def add_paper_to_index(paper_id: int, text: str, owner_id: int, is_public: bool):
    embedding = generate_embedding(text)
    embedding = embedding.reshape(1, -1).astype('float32')
    
    user_index, user_meta = get_or_create_user_index(owner_id)
    user_index.add(embedding)
    user_meta[paper_id] = {"text": text[:500]}
    save_user_index(owner_id, user_index, user_meta)
    
    if is_public:
        public_index, public_meta = get_public_index()
        public_index.add(embedding)
        public_meta[paper_id] = {"text": text[:500], "owner_id": owner_id}
        save_public_index(public_index, public_meta)


def remove_paper_from_index(paper_id: int, owner_id: int, is_public: bool):
    user_index, user_meta = get_or_create_user_index(owner_id)
    if paper_id in user_meta:
        del user_meta[paper_id]
        save_user_index(owner_id, user_index, user_meta)
    
    if is_public:
        public_index, public_meta = get_public_index()
        if paper_id in public_meta:
            del public_meta[paper_id]
            save_public_index(public_index, public_meta)


def search_user_papers(user_id: int, query: str, k: int = 5):
    index, metadata = get_or_create_user_index(user_id)
    if index.ntotal == 0:
        return [], []
    
    query_embedding = generate_embedding(query)
    distances, indices = search_index(index, query_embedding, k)
    
    paper_ids = list(metadata.keys())
    results = [paper_ids[i] for i in indices if i < len(paper_ids)]
    return distances.tolist(), results


def search_public_papers(query: str, k: int = 5):
    index, metadata = get_public_index()
    if index.ntotal == 0:
        return [], []
    
    query_embedding = generate_embedding(query)
    distances, indices = search_index(index, query_embedding, k)
    
    paper_ids = list(metadata.keys())
    results = [paper_ids[i] for i in indices if i < len(paper_ids)]
    return distances.tolist(), results
