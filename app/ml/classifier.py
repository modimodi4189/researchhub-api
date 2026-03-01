from transformers import pipeline

classifier = None

DEFAULT_CATEGORIES = [
    "computer science",
    "machine learning",
    "artificial intelligence",
    "physics",
    "biology",
    "chemistry",
    "mathematics",
    "medicine",
    "economics",
    "psychology"
]


def get_classifier():
    global classifier
    if classifier is None:
        classifier = pipeline(
            "zero-shot-classification",
            model="facebook/bart-large-mnli",
            device=-1  # CPU
        )
    return classifier


def classify_paper(text: str, candidate_labels: list = None) -> dict:
    if not text or len(text.strip()) < 50:
        return {"category": "unknown", "confidence": 0.0}
    
    if candidate_labels is None:
        candidate_labels = DEFAULT_CATEGORIES
    
    classifier = get_classifier()
    
    # Truncate text if too long
    text = text[:1500]
    
    try:
        result = classifier(
            text,
            candidate_labels=candidate_labels,
            multi_label=False
        )
        return {
            "category": result['labels'][0],
            "confidence": result['scores'][0]
        }
    except Exception as e:
        return {"category": "unknown", "confidence": 0.0, "error": str(e)}


def get_default_categories() -> list:
    return DEFAULT_CATEGORIES
