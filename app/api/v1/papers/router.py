from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.database import get_db
from app.db.models import Paper, User
from app.schemas.schemas import PaperCreate, PaperUpdate, PaperResponse, PaginationResponse
from app.api.deps import get_current_user
from app.ml.summarizer import summarize_text
from app.ml.classifier import classify_paper
from app.ml.index_manager import add_paper_to_index
from app.core.logging import logger

router = APIRouter(prefix="/papers", tags=["Papers"])


@router.post("", response_model=PaperResponse, status_code=status.HTTP_201_CREATED)
async def create_paper(
    paper: PaperCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> PaperResponse:
    new_paper = Paper(
        title=paper.title,
        abstract=paper.abstract,
        content=paper.content,
        is_public=paper.is_public,
        category_id=paper.category_id,
        owner_id=current_user.id
    )
    
    db.add(new_paper)
    await db.commit()
    await db.refresh(new_paper)
    
    logger.info(f"User {current_user.id} created paper {new_paper.id}: {new_paper.title}")
    
    if new_paper.content:
        try:
            add_paper_to_index(
                paper_id=new_paper.id,
                text=new_paper.content,
                owner_id=current_user.id,
                is_public=new_paper.is_public
            )
        except Exception as e:
            logger.error(f"Error adding to index: {e}")
    
    return new_paper


@router.get("", response_model=PaginationResponse[PaperResponse])
async def get_papers(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> PaginationResponse[PaperResponse]:
    offset = (page - 1) * limit
    
    count_result = await db.execute(
        select(func.count()).where(Paper.owner_id == current_user.id)
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
        pages=pages
    )
    return papers


@router.get("/{paper_id}", response_model=PaperResponse)
async def get_paper(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
    current_user: User = Depends(get_current_user)
) -> PaperResponse:
    result = await db.execute(select(Paper).where(Paper.id == paper_id))
    paper = result.scalar_one_or_none()
    
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    if paper.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this paper")
    
    update_data = paper_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(paper, field, value)
    
    await db.commit()
    await db.refresh(paper)
    
    logger.info(f"User {current_user.id} updated paper {paper_id}")
    
    return paper


@router.delete("/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_paper(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Paper).where(Paper.id == paper_id))
    paper = result.scalar_one_or_none()
    
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    if paper.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this paper")
    
    await db.delete(paper)
    await db.commit()
    
    logger.info(f"User {current_user.id} deleted paper {paper_id}")
    
    return None


@router.post("/{paper_id}/summarize")
async def summarize_paper(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    result = await db.execute(select(Paper).where(Paper.id == paper_id))
    paper = result.scalar_one_or_none()
    
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    if not paper.is_public and paper.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if not paper.content:
        return {"summary": "No content to summarize"}
    
    summary = summarize_text(paper.content)
    return {"paper_id": paper_id, "summary": summary}


@router.post("/{paper_id}/classify")
async def classify_paper_endpoint(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    result = await db.execute(select(Paper).where(Paper.id == paper_id))
    paper = result.scalar_one_or_none()
    
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    if not paper.is_public and paper.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    text_to_classify = paper.content or paper.abstract or paper.title
    if not text_to_classify:
        return {"category": "unknown", "confidence": 0.0}
    
    classification = classify_paper(text_to_classify)
    return {"paper_id": paper_id, **classification}
