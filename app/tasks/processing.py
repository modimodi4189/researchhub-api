from app.celery import celery_app
from app.ml.index_manager import add_paper_to_index
from app.ml.summarizer import summarize_text
from app.ml.classifier import classify_paper


@celery_app.task(name="process_paper")
def process_paper(paper_id: int, content: str, owner_id: int, is_public: bool):
    """Process paper: add to index, classify, summarize."""
    try:
        if content:
            add_paper_to_index(paper_id, content, owner_id, is_public)
        return {"status": "completed", "paper_id": paper_id}
    except Exception as e:
        return {"status": "error", "paper_id": paper_id, "message": str(e)}


@celery_app.task(name="generate_summary")
def generate_summary(paper_id: int, content: str):
    """Generate summary for a paper."""
    try:
        summary = summarize_text(content)
        return {"status": "completed", "paper_id": paper_id, "summary": summary}
    except Exception as e:
        return {"status": "error", "paper_id": paper_id, "message": str(e)}


@celery_app.task(name="classify_paper_task")
def classify_paper_task(paper_id: int, text: str):
    """Classify a paper."""
    try:
        result = classify_paper(text)
        return {"status": "completed", "paper_id": paper_id, **result}
    except Exception as e:
        return {"status": "error", "paper_id": paper_id, "message": str(e)}
