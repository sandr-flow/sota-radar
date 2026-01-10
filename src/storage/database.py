"""Database connection and session management."""

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.config.settings import settings
from src.storage.models import Base

# Singleton engine instance
_engine: Engine | None = None


def get_engine() -> Engine:
    """Get or create SQLAlchemy engine singleton.

    Returns:
        SQLAlchemy engine.
    """
    global _engine
    if _engine is None:
        # Ensure parent directory exists
        settings.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        _engine = create_engine(
            f"sqlite:///{settings.DB_PATH}", 
            echo=False,
            # SQLite specific usage for single-threaded/low-concurrency
            connect_args={"check_same_thread": False} 
        )
    return _engine


def get_session() -> Session:
    """Create database session using singleton engine.

    Returns:
        SQLAlchemy session.
    """
    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return SessionLocal()


def init_db():
    """Initialize database schema."""
    engine = get_engine()
    Base.metadata.create_all(engine)
