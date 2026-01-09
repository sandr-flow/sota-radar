"""Repository for paper storage with deduplication."""

import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.paper import Paper
from src.storage.models import PaperModel


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
        """Add multiple papers, skipping duplicates.

        Args:
            papers: List of papers to add.

        Returns:
            Tuple of (added_count, skipped_count).
        """
        added = 0
        skipped = 0
        for paper in papers:
            if self.add(paper):
                added += 1
            else:
                skipped += 1
        return added, skipped

    def get_unsummarized(self, limit: int = 100) -> list[PaperModel]:
        """Get papers without summaries.

        Args:
            limit: Maximum number of papers to return.

        Returns:
            List of PaperModel objects.
        """
        stmt = (
            select(PaperModel)
            .where(PaperModel.summary.is_(None))
            .order_by(PaperModel.published.desc())
            .limit(limit)
        )
        return list(self.session.execute(stmt).scalars().all())

    def update_summary(self, paper_id: int, summary: str) -> None:
        """Update paper summary.

        Args:
            paper_id: Paper database ID.
            summary: Generated summary text.
        """
        stmt = select(PaperModel).where(PaperModel.id == paper_id)
        paper = self.session.execute(stmt).scalar_one()
        paper.summary = summary
        paper.summarized_at = datetime.utcnow()
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

    def count(self) -> int:
        """Get total paper count.

        Returns:
            Number of papers in database.
        """
        from sqlalchemy import func
        stmt = select(func.count(PaperModel.id))
        return self.session.execute(stmt).scalar() or 0
