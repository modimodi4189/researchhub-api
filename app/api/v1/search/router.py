from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.db.models import Paper, User
from app.schemas.schemas import PaperResponse, PaginationResponse
from app.api.deps import get_current_user
from app.ml.index_manager import search_user_papers as search_user_papers_idx, search_public_papers as search_public_papers_idx

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("/my", response_model=PaginationResponse[PaperResponse])
async def search_my_papers(
    q: str = Query(..., min_length=1, description="Search query"),
    k: int = Query(5, ge=1, le=20, description="Max results to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> PaginationResponse[PaperResponse]:
    _, paper_ids = search_user_papers_idx(current_user.id, q, k)
    
    if not paper_ids:
        return PaginationResponse(items=[], total=0, page=1, limit=k, pages=0)
    
    result = await db.execute(
        select(Paper).where(Paper.id.in_(paper_ids))
    )
    papers = result.scalars().all()
    
    return PaginationResponse(
        items=list(papers),
        total=len(papers),
        page=1,
        limit=k,
        pages=1
    )


@router.get("/public", response_model=PaginationResponse[PaperResponse])
async def search_public_papers(
    q: str = Query(..., min_length=1, description="Search query"),
    k: int = Query(5, ge=1, le=20, description="Max results to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> PaginationResponse[PaperResponse]:
    _, paper_ids = search_public_papers_idx(q, k)
    
    if not paper_ids:
        return PaginationResponse(items=[], total=0, page=1, limit=k, pages=0)
    
    result = await db.execute(
        select(Paper).where(Paper.id.in_(paper_ids))
    )
    papers = result.scalars().all()
    
    return PaginationResponse(
        items=list(papers),
        total=len(papers),
        page=1,
        limit=k,
        pages=1
    )


@router.get("/similar/{paper_id}", response_model=PaginationResponse[PaperResponse])
async def find_similar_papers(
    paper_id: int,
    k: int = Query(5, ge=1, le=20, description="Max results to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> PaginationResponse[PaperResponse]:
    result = await db.execute(select(Paper).where(Paper.id == paper_id))
    paper = result.scalar_one_or_none()
    
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    if not paper.is_public and paper.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot find similar to private paper")
    
    _, paper_ids = search_public_papers_idx(paper.content or paper.title, k)
    
    if not paper_ids:
        return PaginationResponse(items=[], total=0, page=1, limit=k, pages=0)
    
    result = await db.execute(
        select(Paper).where(Paper.id.in_(paper_ids))
    )
    papers = result.scalars().all()
    
    return PaginationResponse(
        items=list(papers),
        total=len(papers),
        page=1,
        limit=k,
        pages=1
    )
