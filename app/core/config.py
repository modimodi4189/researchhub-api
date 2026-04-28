from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    APP_NAME: str = "ResearchHub API"
    DEBUG: bool = False
    REDIS_URL: str = "redis://localhost:6379/0"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    FAISS_INDEX_DIR: str = "ml_artifacts"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
