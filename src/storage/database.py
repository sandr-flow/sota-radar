"""Database connection and session management."""

from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.config.settings import settings
from src.storage.models import Base

# Singleton engine instance
_engine: Engine | None = None
# Singleton sessionmaker instance
_SessionLocal: sessionmaker | None = None


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
    """Create database session using singleton engine and sessionmaker.

    Returns:
        SQLAlchemy session.
    """
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(),
            autoflush=False,
            autocommit=False
        )
    return _SessionLocal()


@contextmanager
def session_scope():
    """Provide transactional scope around a series of operations.
    
    Automatically handles commit, rollback, and session cleanup.
    
    Usage:
        with session_scope() as session:
            repo = PaperRepository(session)
            papers = repo.get_recent()
    
    Yields:
        SQLAlchemy session.
    """
    init_db()
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db():
    """Initialize database schema."""
    engine = get_engine()
    Base.metadata.create_all(engine)
