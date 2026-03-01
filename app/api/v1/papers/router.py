from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.db.models import Paper, User
from app.schemas.schemas import PaperCreate, PaperUpdate, PaperResponse
from app.api.deps import get_current_user
from app.ml.summarizer import summarize_text
from app.ml.classifier import classify_paper
from app.ml.index_manager import add_paper_to_index

router = APIRouter(prefix="/papers", tags=["Papers"])


@router.post("", response_model=PaperResponse, status_code=status.HTTP_201_CREATED)
async def create_paper(
    paper: PaperCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
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
    
    if new_paper.content:
        try:
            add_paper_to_index(
                paper_id=new_paper.id,
                text=new_paper.content,
                owner_id=current_user.id,
                is_public=new_paper.is_public
            )
        except Exception as e:
            print(f"Error adding to index: {e}")
    
    return new_paper


@router.get("", response_model=List[PaperResponse])
async def get_papers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Paper).where(Paper.owner_id == current_user.id)
    )
    papers = result.scalars().all()
    return papers


@router.get("/{paper_id}", response_model=PaperResponse)
async def get_paper(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
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
):
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
    
    return None


@router.post("/{paper_id}/summarize")
async def summarize_paper(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
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
):
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
