from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings


settings = get_settings()

database_engine = create_engine(
    settings.database_url,
    echo=False,
    future=True,
    pool_pre_ping=True,  # keep connections healthy on MySQL
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=database_engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
