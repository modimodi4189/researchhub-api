import asyncio
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.executor import ml_executor
from app.core.logging import logger
from app.db.database import get_db
from app.db.models import Paper, User, Category
from app.ml.classifier import classify_paper
from app.ml.summarizer import summarize_text
from app.schemas.schemas import PaperCreate, PaperUpdate, PaperResponse, PaperListResponse, PaginationResponse
from app.api.deps import get_current_user
from app.tasks.processing import (
    process_paper,
    remove_paper_from_index_task,
    update_paper_index_task,
)

router = APIRouter(prefix="/papers", tags=["Papers"])


def _paper_index_text(paper: Paper) -> str | None:
    return paper.content or paper.abstract or paper.title


@router.post("", response_model=PaperResponse, status_code=status.HTTP_201_CREATED)
async def create_paper(
    paper: PaperCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaperResponse:
    new_paper = Paper(
        title=paper.title,
        abstract=paper.abstract,
        content=paper.content,
        is_public=paper.is_public,
        category_id=paper.category_id,
        owner_id=current_user.id,
    )
    db.add(new_paper)
    await db.commit()
    await db.refresh(new_paper)

    logger.info(f"User {current_user.id} created paper {new_paper.id}: {new_paper.title}")

    # Dispatch to Celery — indexing runs in the background worker, not the API process.
    index_text = _paper_index_text(new_paper)
    if index_text:
        process_paper.delay(new_paper.id, index_text, current_user.id, new_paper.is_public)

    return new_paper


@router.get("", response_model=PaginationResponse[PaperListResponse])
async def get_papers(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginationResponse[PaperListResponse]:
    offset = (page - 1) * limit

    count_result = await db.execute(
        select(func.count(Paper.id)).where(Paper.owner_id == current_user.id)
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(Paper)
        .where(Paper.owner_id == current_user.id)
        .offset(offset)
        .limit(limit)
    )
    papers = result.scalars().all()
    pages = (total + limit - 1) // limit if total > 0 else 0

    return PaginationResponse(
        items=list(papers),
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


@router.get("/{paper_id}", response_model=PaperResponse)
async def get_paper(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaperResponse:
    result = await db.execute(select(Paper).where(Paper.id == paper_id))
    paper = result.scalar_one_or_none()

    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    if not paper.is_public and paper.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this paper")

    return paper


@router.patch("/{paper_id}", response_model=PaperResponse)
async def update_paper(
    paper_id: int,
    paper_update: PaperUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaperResponse:
    result = await db.execute(select(Paper).where(Paper.id == paper_id))
    paper = result.scalar_one_or_none()

    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    if paper.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this paper")

    old_index_text = _paper_index_text(paper)
    old_is_public = paper.is_public
    old_owner_id = paper.owner_id

    update_data = paper_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(paper, field, value)

    await db.commit()
    await db.refresh(paper)

    new_index_text = _paper_index_text(paper)
    should_update_index = (
        old_index_text != new_index_text
        or old_is_public != paper.is_public
        or old_owner_id != paper.owner_id
    )
    if should_update_index:
        update_paper_index_task.delay(
            paper.id,
            new_index_text,
            paper.owner_id,
            paper.is_public,
            old_owner_id,
        )

    logger.info(f"User {current_user.id} updated paper {paper_id}")
    return paper


@router.delete("/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_paper(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    result = await db.execute(select(Paper).where(Paper.id == paper_id))
    paper = result.scalar_one_or_none()

    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    if paper.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this paper")

    had_index_text = bool(_paper_index_text(paper))
    was_public = paper.is_public

    await db.delete(paper)
    await db.commit()

    # Dispatch index cleanup to Celery — keeps all FAISS writes in one process.
    if had_index_text:
        remove_paper_from_index_task.delay(paper_id, current_user.id, was_public)

    logger.info(f"User {current_user.id} deleted paper {paper_id}")


@router.post("/{paper_id}/summarize", response_model=PaperResponse)
async def summarize_paper(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaperResponse:
    result = await db.execute(select(Paper).where(Paper.id == paper_id))
    paper = result.scalar_one_or_none()

    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    if paper.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    if not paper.content:
        raise HTTPException(status_code=422, detail="Paper has no content to summarize")

    loop = asyncio.get_running_loop()
    summary = await loop.run_in_executor(ml_executor, summarize_text, paper.content)

    paper.summary = summary
    await db.commit()
    await db.refresh(paper)

    logger.info(f"Generated summary for paper {paper_id}")
    return paper


@router.post("/{paper_id}/classify", response_model=PaperResponse)
async def classify_paper_endpoint(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaperResponse:
    result = await db.execute(select(Paper).where(Paper.id == paper_id))
    paper = result.scalar_one_or_none()

    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    if paper.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    text_to_classify = paper.content or paper.abstract or paper.title
    if not text_to_classify:
        raise HTTPException(status_code=422, detail="Paper has no text to classify")

    loop = asyncio.get_running_loop()
    classification = await loop.run_in_executor(ml_executor, classify_paper, text_to_classify)

    category_name = classification.get("category")
    if category_name and category_name != "unknown":
        cat_result = await db.execute(
            select(Category).where(Category.name == category_name)
        )
        category = cat_result.scalar_one_or_none()
        if not category:
            category = Category(name=category_name)
            db.add(category)
            await db.flush()

        paper.category_id = category.id

    await db.commit()
    await db.refresh(paper)

    logger.info(f"Classified paper {paper_id}: {category_name}")
    return paper
