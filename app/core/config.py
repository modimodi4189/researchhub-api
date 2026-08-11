
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    APP_NAME: str = "ResearchHub API"
    DEBUG: bool = False
    REDIS_URL: str = "redis://localhost:6379/0"
    CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:8000"]
    )
    FAISS_INDEX_DIR: str = "ml_artifacts"

    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_must_be_set(cls, value: str) -> str:
        value = value.strip()
        placeholder_values = {
            "replace-this-with-a-real-secret-key",
            "change-me",
            "changeme",
        }
        if not value or value.lower() in placeholder_values:
            raise ValueError("SECRET_KEY must be set to a generated secret value")
        return value

    @model_validator(mode="after")
    def wildcard_cors_requires_debug(self):
        if "*" in self.CORS_ORIGINS and not self.DEBUG:
            raise ValueError("CORS_ORIGINS cannot include '*' unless DEBUG=True")
        return self

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()
