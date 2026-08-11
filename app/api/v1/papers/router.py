import asyncio

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.core.executor import ml_executor
from app.core.logging import logger
from app.db.database import get_db
from app.db.models import Paper, User, Category
from app.ml.classifier import DEFAULT_CATEGORIES, classify_paper
from app.schemas.schemas import PaperCreate, PaperUpdate, PaperResponse, PaperListResponse, PaginationResponse
from app.api.deps import get_current_user
from app.tasks.processing import (
    process_paper,
    remove_paper_from_index_task,
    summarize_paper_task,
    update_paper_index_task,
)

router = APIRouter(prefix="/papers", tags=["Papers"])


def _paper_index_text(paper: Paper) -> str | None:
    return paper.content or paper.abstract or paper.title


async def _ensure_category_exists(category_id: int | None, db: AsyncSession) -> None:
    if category_id is None:
        return

    result = await db.execute(select(Category.id).where(Category.id == category_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Category not found")


async def _get_category_by_name(name: str, db: AsyncSession) -> Category | None:
    return (
        await db.execute(
            select(Category).where(func.lower(Category.name) == name.strip().lower())
        )
    ).scalar_one_or_none()


def _canonical_category_name(name: str) -> str:
    cleaned_name = name.strip()
    for category in DEFAULT_CATEGORIES:
        if category.lower() == cleaned_name.lower():
            return category
    return cleaned_name


@router.post("", response_model=PaperResponse, status_code=status.HTTP_201_CREATED)
async def create_paper(
    paper: PaperCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaperResponse:
    await _ensure_category_exists(paper.category_id, db)

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

    if new_paper.category_id:
        await db.refresh(new_paper, attribute_names=["category"])

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
        .options(selectinload(Paper.category))
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
    result = await db.execute(
        select(Paper).options(selectinload(Paper.category)).where(Paper.id == paper_id)
    )
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
    result = await db.execute(
        select(Paper).options(selectinload(Paper.category)).where(Paper.id == paper_id)
    )
    paper = result.scalar_one_or_none()

    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    if paper.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this paper")

    old_index_text = _paper_index_text(paper)
    old_is_public = paper.is_public
    old_owner_id = paper.owner_id

    update_data = paper_update.model_dump(exclude_unset=True)
    if "category_id" in update_data:
        await _ensure_category_exists(update_data["category_id"], db)

    for field, value in update_data.items():
        setattr(paper, field, value)

    await db.commit()
    await db.refresh(paper)
    if paper.category_id:
        await db.refresh(paper, attribute_names=["category"])

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
    result = await db.execute(
        select(Paper).options(selectinload(Paper.category)).where(Paper.id == paper_id)
    )
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


@router.post(
    "/{paper_id}/summarize",
    response_model=PaperResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def summarize_paper(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaperResponse:
    result = await db.execute(
        select(Paper).options(selectinload(Paper.category)).where(Paper.id == paper_id)
    )
    paper = result.scalar_one_or_none()

    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    if paper.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    if not paper.content:
        raise HTTPException(status_code=422, detail="Paper has no content to summarize")
    if paper.summary_status in {"queued", "processing"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Summary generation is already in progress",
        )

    paper.summary_status = "queued"
    paper.summary_error = None
    await db.commit()
    await db.refresh(paper)

    summarize_paper_task.delay(paper.id)

    logger.info(f"Queued summary generation for paper {paper_id}")
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
    try:
        classification = await loop.run_in_executor(ml_executor, classify_paper, text_to_classify)
    except Exception as exc:
        logger.exception(f"Failed to classify paper {paper_id}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Paper classification failed",
        ) from exc

    category_name = classification.get("category")
    if category_name and category_name != "unknown":
        category_name = _canonical_category_name(category_name)
        category = await _get_category_by_name(category_name, db)
        if not category:
            category = Category(name=category_name)
            db.add(category)
            await db.flush()
        elif category.name != category_name:
            category.name = category_name

        paper.category_id = category.id
        paper.category = category

    await db.commit()
    await db.refresh(paper)
    if paper.category_id:
        await db.refresh(paper, attribute_names=["category"])

    logger.info(f"Classified paper {paper_id}: {category_name}")
    return paper
