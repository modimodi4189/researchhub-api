import numpy as np
from sentence_transformers import SentenceTransformer

model = None


def get_embedding_model():
    global model
    if model is None:
        model = SentenceTransformer('all-MiniLM-L6-v2')
    return model


def generate_embedding(text: str) -> np.ndarray:
    embed_model = get_embedding_model()
    return embed_model.encode(text, convert_to_numpy=True)
