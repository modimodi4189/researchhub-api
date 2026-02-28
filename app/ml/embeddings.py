from sentence_transformers import SentenceTransformer
import numpy as np

model = None


def get_embedding_model():
    global model
    if model is None:
        model = SentenceTransformer('all-MiniLM-L6-v2')
    return model


def generate_embedding(text: str) -> np.ndarray:
    model = get_embedding_model()
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding


def generate_embeddings_batch(texts: list[str]) -> np.ndarray:
    model = get_embedding_model()
    embeddings = model.encode(texts, convert_to_numpy=True)
    return embeddings
