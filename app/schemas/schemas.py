from datetime import datetime
from typing import List, Optional, TypeVar, Generic
from pydantic import BaseModel, EmailStr, ConfigDict

T = TypeVar('T')


class PaginationResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    limit: int
    pages: int


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "email": "user@example.com",
                    "password": "password123"
                }
            ]
        }
    )


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "email": "user@example.com",
                    "password": "password123"
                }
            ]
        }
    )


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
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "title": "Machine Learning Introduction",
                    "abstract": "An overview of ML concepts",
                    "content": "Full paper content goes here...",
                    "is_public": True,
                    "category_id": 1
                }
            ]
        }
    )


class PaperUpdate(BaseModel):
    title: Optional[str] = None
    abstract: Optional[str] = None
    content: Optional[str] = None
    is_public: Optional[bool] = None
    category_id: Optional[int] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "title": "Updated Title",
                    "is_public": False
                }
            ]
        }
    )


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
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "My ML Papers"
                }
            ]
        }
    )


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
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer"
                }
            ]
        }
    )


class TokenData(BaseModel):
    user_id: Optional[int] = None
