from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.api.v1.auth.router import router as auth_router
from app.api.v1.papers.router import router as papers_router
from app.api.v1.collections.router import router as collections_router
from app.api.v1.search.router import router as search_router
from app.db.models import Base
from app.db.database import engine

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered research paper organization API with semantic search",
    version="0.1.0",
    lifespan=lifespan,
)

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please try again later."}
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(papers_router, prefix="/api/v1")
app.include_router(collections_router, prefix="/api/v1")
app.include_router(search_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "Welcome to ResearchHub API"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
