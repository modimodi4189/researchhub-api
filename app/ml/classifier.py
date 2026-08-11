from transformers import pipeline

classifier = None

DEFAULT_CATEGORIES = [
    "Machine Learning",
    "Artificial Intelligence",
    "Software Engineering",
    "Computer Science",
    "Civil Engineering",
    "Mechanical Engineering",
    "Electrical Engineering",
    "History",
    "Physics",
    "Biology",
    "Chemistry",
    "Mathematics",
    "Medicine",
    "Economics",
    "Psychology",
]


def get_classifier():
    global classifier
    if classifier is None:
        classifier = pipeline(
            "zero-shot-classification",
            model="facebook/bart-large-mnli",
            device=-1,  # CPU; use 0 for GPU
        )
    return classifier


def classify_paper(text: str, candidate_labels: list[str] | None = None) -> dict:
    if not text or len(text.strip()) < 50:
        return {"category": "unknown", "confidence": 0.0}

    if candidate_labels is None:
        candidate_labels = DEFAULT_CATEGORIES

    pipe = get_classifier()
    text = text[:1500]

    result = pipe(text, candidate_labels=candidate_labels, multi_label=False)
    return {
        "category": result["labels"][0],
        "confidence": result["scores"][0],
    }
