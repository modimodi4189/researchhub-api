from sentence_transformers import SentenceTransformer
import numpy as np

model = None


def get_embedding_model():
    global model
    if model is None:
        model = SentenceTransformer('all-MiniLM-L6-v2')
    return model


def generate_embedding(text: str) -> np.ndarray:
    embed_model = get_embedding_model()
    return embed_model.encode(text, convert_to_numpy=True)
     


def generate_embeddings_batch(texts: list[str]) -> np.ndarray:
    embed_model = get_embedding_model()
    return embed_model.encode(texts, convert_to_numpy=True)
