from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.core.logging import logger
from app.db.database import get_db
from app.db.models import Collection, Paper, User
from app.schemas.schemas import (
    CollectionCreate,
    CollectionUpdate,
    CollectionResponse,
    CollectionWithPapers,
    PaginationResponse,
)
from app.api.deps import get_current_user

router = APIRouter(prefix="/collections", tags=["Collections"])


@router.post("", response_model=CollectionResponse, status_code=status.HTTP_201_CREATED)
async def create_collection(
    collection: CollectionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CollectionResponse:
    new_collection = Collection(name=collection.name, owner_id=current_user.id)
    db.add(new_collection)
    await db.commit()
    await db.refresh(new_collection)

    logger.info(f"User {current_user.id} created collection {new_collection.id}")
    return new_collection


@router.get("", response_model=PaginationResponse[CollectionResponse])
async def get_collections(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginationResponse[CollectionResponse]:
    offset = (page - 1) * limit

    count_result = await db.execute(
        select(func.count(Collection.id)).where(Collection.owner_id == current_user.id)
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(Collection)
        .where(Collection.owner_id == current_user.id)
        .offset(offset)
        .limit(limit)
    )
    collections = result.scalars().all()
    pages = (total + limit - 1) // limit if total > 0 else 0

    return PaginationResponse(
        items=list(collections),
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


@router.get("/{collection_id}", response_model=CollectionWithPapers)
async def get_collection(
    collection_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CollectionWithPapers:
    result = await db.execute(
        select(Collection)
        .options(selectinload(Collection.papers).selectinload(Paper.category))
        .where(Collection.id == collection_id, Collection.owner_id == current_user.id)
    )
    collection = result.scalar_one_or_none()

    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    return collection


@router.patch("/{collection_id}", response_model=CollectionResponse)
async def update_collection(
    collection_id: int,
    collection_update: CollectionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CollectionResponse:
    result = await db.execute(
        select(Collection).where(
            Collection.id == collection_id, Collection.owner_id == current_user.id
        )
    )
    collection = result.scalar_one_or_none()

    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    update_data = collection_update.model_dump(exclude_unset=True)
    if not update_data:
        return collection
 
    for field, value in update_data.items():
        setattr(collection, field, value)
 
    await db.commit()
    await db.refresh(collection)

    logger.info(f"User {current_user.id} updated collection {collection_id}")
    return collection


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_collection(
    collection_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    result = await db.execute(
        select(Collection).where(
            Collection.id == collection_id, Collection.owner_id == current_user.id
        )
    )
    collection = result.scalar_one_or_none()

    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    await db.delete(collection)
    await db.commit()

    logger.info(f"User {current_user.id} deleted collection {collection_id}")


@router.post(
    "/{collection_id}/papers/{paper_id}", status_code=status.HTTP_201_CREATED
)
async def add_paper_to_collection(
    collection_id: int,
    paper_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    collection_result = await db.execute(
        select(Collection)
        .options(selectinload(Collection.papers))
        .where(Collection.id == collection_id, Collection.owner_id == current_user.id)
    )
    collection = collection_result.scalar_one_or_none()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    paper_result = await db.execute(
        select(Paper).where(Paper.id == paper_id, Paper.owner_id == current_user.id)
    )
    paper = paper_result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found or not owned by user")

    if paper not in collection.papers:
        collection.papers.append(paper)
        await db.commit()
        logger.info(f"User {current_user.id} added paper {paper_id} to collection {collection_id}")

    return {"message": "Paper added to collection"}


@router.delete(
    "/{collection_id}/papers/{paper_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_paper_from_collection(
    collection_id: int,
    paper_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    collection_result = await db.execute(
        select(Collection)
        .options(selectinload(Collection.papers))
        .where(Collection.id == collection_id, Collection.owner_id == current_user.id)
    )
    collection = collection_result.scalar_one_or_none()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    paper = next((p for p in collection.papers if p.id == paper_id), None)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found in collection")

    collection.papers.remove(paper)
    await db.commit()

    logger.info(f"User {current_user.id} removed paper {paper_id} from collection {collection_id}")
