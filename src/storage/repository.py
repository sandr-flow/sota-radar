"""Repository for paper storage with deduplication."""

import json
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from src.models.paper import Paper
from src.storage.models import PaperModel, UserModel


class PaperRepository:
    """Repository for storing and retrieving papers.

    Handles conversion between Paper dataclass and PaperModel,
    and implements deduplication logic.
    """

    def __init__(self, session: Session):
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy session.
        """
        self.session = session

    def exists(self, source: str, source_id: str) -> bool:
        """Check if paper already exists in database.

        Args:
            source: Source identifier.
            source_id: ID within the source.

        Returns:
            True if paper exists.
        """
        stmt = select(PaperModel).where(
            PaperModel.source == source,
            PaperModel.source_id == source_id,
        )
        result = self.session.execute(stmt).scalar_one_or_none()
        return result is not None

    def add(self, paper: Paper) -> PaperModel | None:
        """Add paper to database if not exists.

        Args:
            paper: Paper to add.

        Returns:
            Created PaperModel or None if already exists.
        """
        if self.exists(paper.source, paper.source_id):
            return None

        model = PaperModel(
            source=paper.source,
            source_id=paper.source_id,
            title=paper.title,
            abstract=paper.abstract,
            authors=json.dumps(paper.authors),
            published=paper.published,
            url=paper.url,
            pdf_url=paper.pdf_url,
        )
        self.session.add(model)
        self.session.commit()
        return model

    def add_many(self, papers: list[Paper]) -> tuple[int, int]:
        """Add multiple papers, skipping duplicates using bulk insert.

        Args:
            papers: List of papers to add.

        Returns:
            Tuple of (added_count, skipped_count).
        """
        if not papers:
            return 0, 0

        # Prepare list of dicts for bulk insert
        values = [
            {
                "source": paper.source,
                "source_id": paper.source_id,
                "title": paper.title,
                "abstract": paper.abstract,
                "authors": json.dumps(paper.authors),
                "published": paper.published,
                "url": paper.url,
                "pdf_url": paper.pdf_url,
                "created_at": datetime.now(timezone.utc)
            }
            for paper in papers
        ]

        stmt = insert(PaperModel).values(values)
        
        # On conflict do nothing (deduplication)
        stmt = stmt.on_conflict_do_nothing(
            index_elements=["source", "source_id"]
        )
        
        result = self.session.execute(stmt)
        self.session.commit()
        
        added_count = result.rowcount
        skipped_count = len(papers) - added_count
        
        return added_count, skipped_count

    def get_by_id(self, paper_id: int) -> PaperModel | None:
        """Get paper by database ID.

        Args:
            paper_id: Paper database ID.

        Returns:
            PaperModel or None if not found.
        """
        stmt = select(PaperModel).where(PaperModel.id == paper_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_unsummarized(self, limit: int = 100) -> list[PaperModel]:
        """Get papers without summaries.

        Args:
            limit: Maximum number of papers to return.

        Returns:
            List of PaperModel objects.
        """
        stmt = (
            select(PaperModel)
            .where(PaperModel.summary_json.is_(None))
            .order_by(PaperModel.published.desc())
            .limit(limit)
        )
        return list(self.session.execute(stmt).scalars().all())

    def update_summary(self, paper_id: int, summary_dict: dict[str, str]) -> None:
        """Update paper summary with bilingual JSON.

        Args:
            paper_id: Paper database ID.
            summary_dict: Dict with language keys, e.g. {"en": "...", "ru": "..."}.
        """
        stmt = select(PaperModel).where(PaperModel.id == paper_id)
        paper = self.session.execute(stmt).scalar_one()
        paper.summary_json = json.dumps(summary_dict, ensure_ascii=False)
        paper.summarized_at = datetime.now(timezone.utc)
        self.session.commit()

    def get_recent(self, limit: int = 10) -> list[PaperModel]:
        """Get most recent papers.

        Args:
            limit: Number of papers to return.

        Returns:
            List of PaperModel objects.
        """
        stmt = (
            select(PaperModel)
            .order_by(PaperModel.published.desc())
            .limit(limit)
        )
        return list(self.session.execute(stmt).scalars().all())

    def reset_all_summaries(self) -> int:
        """Reset all summaries for re-summarization.

        Uses bulk UPDATE to avoid loading all records into memory.

        Returns:
            Number of papers reset.
        """
        from sqlalchemy import update
        
        stmt = (
            update(PaperModel)
            .where(PaperModel.summary_json.isnot(None))
            .values(summary_json=None, summarized_at=None)
        )
        result = self.session.execute(stmt)
        self.session.commit()
        return result.rowcount

    def count(self) -> int:
        """Get total paper count.

        Returns:
            Number of papers in database.
        """
        stmt = select(func.count(PaperModel.id))
        return self.session.execute(stmt).scalar() or 0
    
    # Priority queue methods for persistent queue
    
    def mark_priority(self, paper_id: int) -> bool:
        """Mark paper for priority summarization.
        
        Args:
            paper_id: Paper database ID.
            
        Returns:
            True if marked, False if already marked or not found.
        """
        paper = self.get_by_id(paper_id)
        if paper is None or paper.priority_requested:
            return False
        paper.priority_requested = True
        self.session.commit()
        return True
    
    def get_priority_papers(self, limit: int = 10) -> list[PaperModel]:
        """Get papers marked for priority summarization.
        
        Args:
            limit: Maximum number of papers to return.
            
        Returns:
            List of unsummarized papers with priority_requested=True.
        """
        stmt = (
            select(PaperModel)
            .where(
                PaperModel.priority_requested == True,
                PaperModel.summary_json.is_(None)
            )
            .order_by(PaperModel.id)  # FIFO order
            .limit(limit)
        )
        return list(self.session.execute(stmt).scalars().all())
    
    def clear_priority(self, paper_id: int) -> None:
        """Clear priority flag after summarization.
        
        Args:
            paper_id: Paper database ID.
        """
        paper = self.get_by_id(paper_id)
        if paper:
            paper.priority_requested = False
            self.session.commit()


class UserRepository:
    """Repository for user preferences."""

    def __init__(self, session: Session):
        """Initialize repository with database session."""
        self.session = session

    def get_or_create(self, telegram_id: int) -> UserModel:
        """Get user by telegram ID or create new.

        Args:
            telegram_id: Telegram user ID.

        Returns:
            UserModel instance.
        """
        stmt = select(UserModel).where(UserModel.telegram_id == telegram_id)
        user = self.session.execute(stmt).scalar_one_or_none()
        if user is None:
            user = UserModel(telegram_id=telegram_id, language="en")
            self.session.add(user)
            self.session.commit()
        return user

    def get_language(self, telegram_id: int) -> str:
        """Get user's preferred language.

        Args:
            telegram_id: Telegram user ID.

        Returns:
            Language code ('en' or 'ru').
        """
        user = self.get_or_create(telegram_id)
        return user.language

    def set_language(self, telegram_id: int, language: str) -> None:
        """Set user's preferred language.

        Args:
            telegram_id: Telegram user ID.
            language: Language code ('en' or 'ru').
        """
        user = self.get_or_create(telegram_id)
        user.language = language
        self.session.commit()

