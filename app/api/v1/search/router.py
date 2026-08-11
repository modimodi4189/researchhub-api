import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.db.database import get_db
from app.db.models import Paper, User
from app.ml.index_manager import (
    search_public_papers as search_public_papers_idx,
)
from app.ml.index_manager import (
    search_user_papers as search_user_papers_idx,
)
from app.schemas.schemas import PaginationResponse, PaperListResponse

router = APIRouter(prefix="/search", tags=["Search"])

def _preserve_order(papers: list[Paper], paper_ids: list[int]) -> list[Paper]:
    """
    Re-order DB results to match the relevance order returned by FAISS.
 
    SQLAlchemy's IN clause does not preserve the order of the input list —
    results come back in the database's internal order. This function maps
    paper_id to Paper and reconstructs the list in FAISS's ranked order,
    ensuring the most semantically similar results appear first.
    """
    paper_map = {p.id: p for p in papers}
    return [paper_map[pid] for pid in paper_ids if pid in paper_map]


@router.get("/my", response_model=PaginationResponse[PaperListResponse])
async def search_my_papers(
    q: str = Query(..., min_length=1, description="Search query"),
    k: int = Query(5, ge=1, le=20, description="Max results to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginationResponse[PaperListResponse]:
    loop = asyncio.get_running_loop()
    _, paper_ids = await loop.run_in_executor(
        None, search_user_papers_idx, current_user.id, q, k
    )

    if not paper_ids:
        return PaginationResponse(items=[], total=0, page=1, limit=k, pages=0)

    result = await db.execute(
        select(Paper).where(
            Paper.id.in_(paper_ids),
            Paper.owner_id == current_user.id,
        ).options(selectinload(Paper.category))
    )
    papers = _preserve_order(result.scalars().all(), paper_ids)

    return PaginationResponse(
        items=papers,
        total=len(papers),
        page=1,
        limit=k,
        pages=1 if papers else 0,
    )


@router.get("/public", response_model=PaginationResponse[PaperListResponse])
async def search_public_papers(
    q: str = Query(..., min_length=1, description="Search query"),
    k: int = Query(5, ge=1, le=20, description="Max results to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginationResponse[PaperListResponse]:
    loop = asyncio.get_running_loop()
    _, paper_ids = await loop.run_in_executor(None, search_public_papers_idx, q, k)

    if not paper_ids:
        return PaginationResponse(items=[], total=0, page=1, limit=k, pages=0)

    result = await db.execute(
        select(Paper).where(
            Paper.id.in_(paper_ids),
            Paper.is_public.is_(True),
        ).options(selectinload(Paper.category))
    )
    papers = _preserve_order(result.scalars().all(), paper_ids)

    return PaginationResponse(
        items=papers,
        total=len(papers),
        page=1,
        limit=k,
        pages=1 if papers else 0,
    )


@router.get("/similar/{paper_id}", response_model=PaginationResponse[PaperListResponse])
async def find_similar_papers(
    paper_id: int,
    k: int = Query(5, ge=1, le=20, description="Max results to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginationResponse[PaperListResponse]:
    paper_result = await db.execute(
        select(Paper).options(selectinload(Paper.category)).where(Paper.id == paper_id)
    )
    paper = paper_result.scalar_one_or_none()

    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    if not paper.is_public and paper.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot find similar papers for a private paper")

    search_text = paper.content or paper.abstract or paper.title
    loop = asyncio.get_running_loop()

    # Search the correct index based on paper visibility.
    if paper.is_public:
        _, paper_ids = await loop.run_in_executor(
            None, search_public_papers_idx, search_text, k + 1
        )
    else:
        _, paper_ids = await loop.run_in_executor(
            None, search_user_papers_idx, current_user.id, search_text, k + 1
        )

    # Exclude the source paper — it is always its own closest match.
    paper_ids = [pid for pid in paper_ids if pid != paper_id][:k]

    if not paper_ids:
        return PaginationResponse(items=[], total=0, page=1, limit=k, pages=0)

    similar_result = await db.execute(
        select(Paper).where(
            Paper.id.in_(paper_ids),
            or_(Paper.is_public.is_(True), Paper.owner_id == current_user.id),
        ).options(selectinload(Paper.category))
    )
    similar_papers = _preserve_order(similar_result.scalars().all(), paper_ids)

    return PaginationResponse(
        items=similar_papers,
        total=len(similar_papers),
        page=1,
        limit=k,
        pages=1 if similar_papers else 0,
    )
