from typing import List, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.db.models import Collection, Paper, User
from app.schemas.schemas import CollectionCreate, CollectionResponse, CollectionWithPapers
from app.api.deps import get_current_user

router = APIRouter(prefix="/collections", tags=["Collections"])


@router.post("", response_model=CollectionResponse, status_code=status.HTTP_201_CREATED)
async def create_collection(
    collection: CollectionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> CollectionResponse:
    new_collection = Collection(
        name=collection.name,
        owner_id=current_user.id
    )
    
    db.add(new_collection)
    await db.commit()
    await db.refresh(new_collection)
    
    return new_collection


@router.get("", response_model=List[CollectionResponse])
async def get_collections(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[CollectionResponse]:
    result = await db.execute(
        select(Collection).where(Collection.owner_id == current_user.id)
    )
    collections = result.scalars().all()
    return collections


@router.get("/{collection_id}", response_model=CollectionWithPapers)
async def get_collection(
    collection_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> CollectionWithPapers:
    result = await db.execute(
        select(Collection).where(
            Collection.id == collection_id,
            Collection.owner_id == current_user.id
        )
    )
    collection = result.scalar_one_or_none()
    
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    return collection


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_collection(
    collection_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> None:
    result = await db.execute(
        select(Collection).where(
            Collection.id == collection_id,
            Collection.owner_id == current_user.id
        )
    )
    collection = result.scalar_one_or_none()
    
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    await db.delete(collection)
    await db.commit()
    
    return None


@router.post("/{collection_id}/papers/{paper_id}", status_code=status.HTTP_201_CREATED)
async def add_paper_to_collection(
    collection_id: int,
    paper_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    # Check collection exists and belongs to user
    collection_result = await db.execute(
        select(Collection).where(
            Collection.id == collection_id,
            Collection.owner_id == current_user.id
        )
    )
    collection = collection_result.scalar_one_or_none()
    
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    # Check paper exists and user owns it
    paper_result = await db.execute(
        select(Paper).where(
            Paper.id == paper_id,
            Paper.owner_id == current_user.id
        )
    )
    paper = paper_result.scalar_one_or_none()
    
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found or not owned by user")
    
    # Add paper to collection
    if paper not in collection.papers:
        collection.papers.append(paper)
        await db.commit()
    
    return {"message": "Paper added to collection"}


@router.delete("/{collection_id}/papers/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_paper_from_collection(
    collection_id: int,
    paper_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> None:
    # Check collection exists and belongs to user
    collection_result = await db.execute(
        select(Collection).where(
            Collection.id == collection_id,
            Collection.owner_id == current_user.id
        )
    )
    collection = collection_result.scalar_one_or_none()
    
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    # Check paper is in collection
    paper = next((p for p in collection.papers if p.id == paper_id), None)
    
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found in collection")
    
    collection.papers.remove(paper)
    await db.commit()
    
    return None
