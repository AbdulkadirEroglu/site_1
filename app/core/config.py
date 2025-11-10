from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    project_name: str = Field(default="Product Catalog Platform", env="PROJECT_NAME")
    database_url: str = Field(..., env="DATABASE_URL")
    secret_key: str = Field(..., env="SECRET_KEY")
    session_cookie_name: str = Field(default="admin_session", env="SESSION_COOKIE_NAME")
    session_cookie_secure: bool = Field(default=True, env="SESSION_COOKIE_SECURE")
    session_cookie_max_age: int | None = Field(default=60 * 60 * 4, env="SESSION_COOKIE_MAX_AGE")
    session_cookie_same_site: Literal["lax", "strict", "none"] = Field(
        default="lax", env="SESSION_COOKIE_SAME_SITE"
    )
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    login_rate_limit_window_seconds: int = Field(default=300, env="LOGIN_RATE_LIMIT_WINDOW_SECONDS")
    login_rate_limit_max_attempts: int = Field(default=5, env="LOGIN_RATE_LIMIT_MAX_ATTEMPTS")

    @model_validator(mode="after")
    def validate_security(self) -> "Settings":
        if len(self.secret_key) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long.")
        if "://" not in self.database_url:
            raise ValueError("DATABASE_URL must be a valid connection string.")
        return self

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
