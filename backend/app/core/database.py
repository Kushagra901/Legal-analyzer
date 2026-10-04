"""
Database configuration and session management.
Initializes SQLAlchemy engine and session factories.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import settings

is_sqlite = settings.DATABASE_URL.startswith("sqlite")
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if is_sqlite else {},
    pool_size=10 if not is_sqlite else 5,
    max_overflow=20 if not is_sqlite else 10,
    pool_pre_ping=True,
    pool_recycle=1800,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency injection helper to yield active DB sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
