"""Paper model for sota-radar."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Paper:
    """Unified paper representation across all sources.

    Attributes:
        source: Source identifier (e.g., "arxiv", "huggingface").
        source_id: Unique ID within the source.
        title: Paper title.
        abstract: Paper abstract.
        authors: List of author names.
        published: Publication date.
        url: Link to the paper page.
        pdf_url: Direct link to PDF, if available.
    """

    source: str
    source_id: str
    title: str
    abstract: str
    authors: list[str]
    published: datetime
    url: str
    pdf_url: str | None = None

    @property
    def unique_id(self) -> str:
        """Return unique identifier across all sources."""
        return f"{self.source}:{self.source_id}"
