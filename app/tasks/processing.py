import asyncio

from app.celery import celery_app
from app.core.logging import logger
from app.db.database import AsyncSessionLocal
from app.db.models import Paper
from app.ml.index_manager import (
    add_paper_to_index,
    remove_paper_from_index,
    update_paper_in_index,
)
from app.ml.summarizer import summarize_text


@celery_app.task(name="process_paper")
def process_paper(paper_id: int, text: str, owner_id: int, is_public: bool):
    """
    Background task: embed the paper text and add it to the FAISS search index.
    Dispatched from create_paper so indexing never blocks the HTTP response.
    """
    try:
        if text:
            add_paper_to_index(paper_id, text, owner_id, is_public)
        logger.info(f"Successfully indexed paper {paper_id}")
        return {"status": "completed", "paper_id": paper_id}
    except Exception:
        logger.exception(f"Error indexing paper {paper_id}")
        raise


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
    except Exception:
        logger.exception(f"Error removing paper {paper_id} from index")
        raise


@celery_app.task(name="update_paper_index_task")
def update_paper_index_task(
    paper_id: int,
    text: str | None,
    owner_id: int,
    is_public: bool,
    previous_owner_id: int | None = None,
):
    """
    Reconcile a paper's FAISS entries after searchable text, visibility, or
    ownership changes.
    """
    try:
        update_paper_in_index(
            paper_id,
            text,
            owner_id,
            is_public,
            previous_owner_id=previous_owner_id,
        )
        logger.info(f"Successfully updated index for paper {paper_id}")
        return {"status": "completed", "paper_id": paper_id}
    except Exception:
        logger.exception(f"Error updating index for paper {paper_id}")
        raise


@celery_app.task(name="summarize_paper_task")
def summarize_paper_task(paper_id: int):
    """
    Generate and persist a paper summary outside the HTTP request path.

    The summarization model may need a large first-time download/load. Keeping
    this work in Celery lets the API return quickly and lets the frontend poll
    the paper status instead of waiting on a long-running request.
    """
    return asyncio.run(_summarize_paper_async(paper_id))


async def _summarize_paper_async(paper_id: int):
    async with AsyncSessionLocal() as db:
        paper = await db.get(Paper, paper_id)
        if paper is None:
            logger.warning(f"Cannot summarize missing paper {paper_id}")
            return {"status": "missing", "paper_id": paper_id}

        paper.summary_status = "processing"
        paper.summary_error = None
        await db.commit()

        try:
            summary = summarize_text(paper.content or "")
        except (OSError, RuntimeError, ValueError) as exc:
            paper.summary_status = "failed"
            paper.summary_error = str(exc)[:1000]
            await db.commit()
            logger.exception(f"Error summarizing paper {paper_id}")
            return {"status": "failed", "paper_id": paper_id}

        paper.summary = summary
        paper.summary_status = "complete"
        paper.summary_error = None
        await db.commit()

        logger.info(f"Successfully summarized paper {paper_id}")
        return {"status": "completed", "paper_id": paper_id}
