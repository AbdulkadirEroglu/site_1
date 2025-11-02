from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    project_name: str = "Product Catalog Platform"
    database_url: str = "postgresql+psycopg://catalog_user:catalog_pass@localhost:5432/catalog"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
