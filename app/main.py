from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1.auth.router import router as auth_router
from app.api.v1.collections.router import router as collections_router
from app.api.v1.papers.router import router as papers_router
from app.api.v1.search.router import router as search_router
from app.core.config import settings
from app.core.limiter import limiter
from app.core.logging import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schema is managed by Alembic migrations.
    # Run `alembic upgrade head` before starting the API.
    # In Docker this is handled automatically by the migrate service.
    logger.info("ResearchHub API starting up")
    yield
    logger.info("ResearchHub API shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered research paper organization API with semantic search",
    version="0.1.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please try again later."},
    )


cors_origins = settings.CORS_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials="*" not in cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(papers_router, prefix="/api/v1")
app.include_router(collections_router, prefix="/api/v1")
app.include_router(search_router, prefix="/api/v1")


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Welcome to ResearchHub API"}


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}
