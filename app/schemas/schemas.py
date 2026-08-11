from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

T = TypeVar("T")

PAPER_TITLE_MAX_LENGTH = 255
PAPER_ABSTRACT_MAX_LENGTH = 10_000
PAPER_CONTENT_MAX_LENGTH = 1_000_000
COLLECTION_NAME_MAX_LENGTH = 255


class PaginationResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    limit: int
    pages: int


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"email": "user@example.com", "password": "password123"}]
        }
    )


class UserLogin(BaseModel):
    email: EmailStr
    password: str

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"email": "user@example.com", "password": "password123"}]
        }
    )


class UserResponse(BaseModel):
    id: int
    email: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer",
                }
            ]
        }
    )


class RefreshRequest(BaseModel):
    refresh_token: str


# ---------------------------------------------------------------------------
# Papers
# ---------------------------------------------------------------------------

class CategoryResponse(BaseModel):
    id: int
    name: str
    description: str | None

    model_config = ConfigDict(from_attributes=True)


class PaperCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=PAPER_TITLE_MAX_LENGTH)
    abstract: str | None = Field(None, max_length=PAPER_ABSTRACT_MAX_LENGTH)
    content: str | None = Field(None, max_length=PAPER_CONTENT_MAX_LENGTH)
    is_public: bool = False
    category_id: int | None = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Title must not be blank")
        return value

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "title": "Machine Learning Introduction",
                    "abstract": "An overview of ML concepts",
                    "content": "Full paper content goes here...",
                    "is_public": True,
                    "category_id": 1,
                }
            ]
        }
    )


class PaperUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=PAPER_TITLE_MAX_LENGTH)
    abstract: str | None = Field(None, max_length=PAPER_ABSTRACT_MAX_LENGTH)
    content: str | None = Field(None, max_length=PAPER_CONTENT_MAX_LENGTH)
    is_public: bool | None = None
    category_id: int | None = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Title must not be blank")
        return value

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"title": "Updated Title", "is_public": False}]
        }
    )


class PaperResponse(BaseModel):
    id: int
    title: str
    abstract: str | None
    content: str | None
    summary: str | None
    summary_status: str
    summary_error: str | None
    is_public: bool
    created_at: datetime
    updated_at: datetime | None
    owner_id: int
    category_id: int | None
    category: CategoryResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class PaperListResponse(BaseModel):
    """Lightweight paper representation for list endpoints. Excludes full content."""

    id: int
    title: str
    abstract: str | None
    summary: str | None
    summary_status: str
    summary_error: str | None
    is_public: bool
    created_at: datetime
    updated_at: datetime | None
    owner_id: int
    category_id: int | None
    category: CategoryResponse | None = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Collections
# ---------------------------------------------------------------------------

class CollectionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=COLLECTION_NAME_MAX_LENGTH)

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Collection name must not be blank")
        return value

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"name": "My ML Papers"}]}
    )


class CollectionUpdate(BaseModel):
    name: str | None = Field(
        None, min_length=1, max_length=COLLECTION_NAME_MAX_LENGTH
    )

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Collection name must not be blank")
        return value

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"name": "Updated Collection Name"}]}
    )


class CollectionResponse(BaseModel):
    id: int
    name: str
    created_at: datetime
    updated_at: datetime | None
    owner_id: int

    model_config = ConfigDict(from_attributes=True)


class CollectionWithPapers(CollectionResponse):
    papers: list[PaperListResponse] = []
