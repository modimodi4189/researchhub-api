from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None


class CategoryResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]

    class Config:
        from_attributes = True


class PaperCreate(BaseModel):
    title: str
    abstract: Optional[str] = None
    content: Optional[str] = None
    is_public: bool = False
    category_id: Optional[int] = None


class PaperUpdate(BaseModel):
    title: Optional[str] = None
    abstract: Optional[str] = None
    content: Optional[str] = None
    is_public: Optional[bool] = None
    category_id: Optional[int] = None


class PaperResponse(BaseModel):
    id: int
    title: str
    abstract: Optional[str]
    content: Optional[str]
    is_public: bool
    created_at: datetime
    owner_id: int
    category_id: Optional[int]

    class Config:
        from_attributes = True


class CollectionCreate(BaseModel):
    name: str


class CollectionResponse(BaseModel):
    id: int
    name: str
    created_at: datetime
    owner_id: int

    class Config:
        from_attributes = True


class CollectionWithPapers(CollectionResponse):
    papers: List[PaperResponse] = []


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_id: Optional[int] = None
