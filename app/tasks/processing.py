from app.celery import celery_app
from app.ml.index_manager import add_paper_to_index, remove_paper_from_index
from app.core.logging import logger


@celery_app.task(name="process_paper")
def process_paper(paper_id: int, content: str, owner_id: int, is_public: bool):
    """
    Background task: embed the paper text and add it to the FAISS search index.
    Dispatched from create_paper so indexing never blocks the HTTP response.
    """
    try:
        if content:
            add_paper_to_index(paper_id, content, owner_id, is_public)
        logger.info(f"Successfully indexed paper {paper_id}")
        return {"status": "completed", "paper_id": paper_id}
    except Exception as e:
        logger.error(f"Error indexing paper {paper_id}: {e}")
        return {"status": "error", "paper_id": paper_id, "message": str(e)}


@celery_app.task(name="remove_paper_from_index_task")
def remove_paper_from_index_task(paper_id: int, owner_id: int, is_public: bool):
    """
    Background task: remove a paper's vector from the FAISS index on deletion.
    Keeping all index writes inside Celery tasks means only one process ever
    writes to the shared ml_artifacts volume, eliminating the write race between
    the API container and the Celery worker container.
    """
    try:
        remove_paper_from_index(paper_id, owner_id, is_public)
        logger.info(f"Successfully removed paper {paper_id} from index")
        return {"status": "completed", "paper_id": paper_id}
    except Exception as e:
        logger.error(f"Error removing paper {paper_id} from index: {e}")
        return {"status": "error", "paper_id": paper_id, "message": str(e)}
