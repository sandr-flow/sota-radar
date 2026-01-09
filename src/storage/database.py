"""Database connection and session management."""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.storage.models import Base

# Default database path
DEFAULT_DB_PATH = Path(__file__).parent.parent.parent / "data" / "sota_radar.db"


def get_engine(db_path: Path | str | None = None):
    """Create SQLAlchemy engine.

    Args:
        db_path: Path to SQLite database. Defaults to data/sota_radar.db.

    Returns:
        SQLAlchemy engine.
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    else:
        db_path = Path(db_path)

    # Ensure parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    return create_engine(f"sqlite:///{db_path}", echo=False)


def get_session(db_path: Path | str | None = None):
    """Create database session.

    Args:
        db_path: Path to SQLite database.

    Returns:
        SQLAlchemy session.
    """
    engine = get_engine(db_path)
    Session = sessionmaker(bind=engine)
    return Session()


def init_db(db_path: Path | str | None = None):
    """Initialize database schema.

    Args:
        db_path: Path to SQLite database.
    """
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)
