"""HuggingFace Daily Papers source implementation for sota-radar."""

import logging
from dataclasses import dataclass
from datetime import datetime

from src.infrastructure.http_client import get_client

logger = logging.getLogger(__name__)

# HuggingFace API constants
HF_DAILY_PAPERS_URL = "https://huggingface.co/api/daily_papers"

# Our tracked arXiv categories
TRACKED_CATEGORIES = {"cs.LG", "cs.CL", "cs.CV", "cs.AI", "cs.NE", "cs.IR", "stat.ML"}


@dataclass
class HFPaper:
    """HuggingFace Daily Paper data."""

    arxiv_id: str
    title: str
    summary: str
    upvotes: int
    published_at: datetime
    categories: list[str] | None = None  # Filled after arXiv lookup


class HuggingFaceSource:
    """HuggingFace Daily Papers source.

    Fetches trending papers from HuggingFace Daily Papers API
    and filters by arXiv categories.
    """

    async def fetch_daily_papers(self, limit: int = 50) -> list[HFPaper]:
        """Fetch daily papers from HuggingFace.

        Args:
            limit: Maximum number of papers to fetch.

        Returns:
            List of HFPaper objects sorted by upvotes.
        """
        client = get_client()
        try:
            response = await client.get(HF_DAILY_PAPERS_URL)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            logger.error(f"Failed to fetch HF daily papers: {e}")
            return []

        papers = []
        for item in data[:limit]:
            paper_data = item.get("paper", {})
            arxiv_id = paper_data.get("id", "")
            
            if not arxiv_id:
                continue

            try:
                published_str = paper_data.get("publishedAt", "")
                published_at = self._parse_date(published_str)
                
                paper = HFPaper(
                    arxiv_id=arxiv_id,
                    title=paper_data.get("title", ""),
                    summary=paper_data.get("summary", ""),
                    upvotes=paper_data.get("upvotes", 0),
                    published_at=published_at,
                )
                papers.append(paper)
            except Exception as e:
                logger.warning(f"Failed to parse HF paper {arxiv_id}: {e}")
                continue

        # Sort by upvotes descending
        papers.sort(key=lambda p: p.upvotes, reverse=True)
        return papers

    async def fetch_filtered_papers(
        self,
        limit: int = 10,
        categories: set[str] | None = None,
    ) -> list[HFPaper]:
        """Fetch daily papers filtered by arXiv categories.

        For papers not in DB, queries arXiv API to get categories.

        Args:
            limit: Maximum number of papers to return.
            categories: Set of arXiv categories to filter by.
                       Defaults to TRACKED_CATEGORIES.

        Returns:
            List of HFPaper objects matching category filter.
        """
        if categories is None:
            categories = TRACKED_CATEGORIES

        # Fetch all daily papers
        all_papers = await self.fetch_daily_papers(limit=100)
        
        if not all_papers:
            return []

        # Filter by categories
        filtered = []
        for paper in all_papers:
            # Check if paper matches our categories
            paper_categories = await self._get_paper_categories(paper.arxiv_id)
            
            if paper_categories:
                paper.categories = paper_categories
                # Check if any category matches
                if categories.intersection(set(paper_categories)):
                    filtered.append(paper)
                    if len(filtered) >= limit:
                        break

        return filtered

    async def _get_paper_categories(self, arxiv_id: str) -> list[str] | None:
        """Get arXiv categories for a paper.

        First checks DB, then queries arXiv API if not found.

        Args:
            arxiv_id: arXiv paper ID (e.g., "2601.09088").

        Returns:
            List of category strings or None if not found.
        """
        # First try to get from DB
        from src.storage import init_db, get_session
        from src.storage.repository import PaperRepository
        
        try:
            init_db()
            session = get_session()
            repo = PaperRepository(session)
            
            # Look up by source_id
            from sqlalchemy import select
            from src.storage.models import PaperModel
            
            stmt = select(PaperModel).where(
                PaperModel.source == "arxiv",
                PaperModel.source_id.like(f"{arxiv_id}%")
            )
            paper = session.execute(stmt).scalar_one_or_none()
            session.close()
            
            if paper:
                # Paper is in DB, it passed our category filter during fetch
                return list(TRACKED_CATEGORIES)  # Assume it matches
        except Exception as e:
            logger.warning(f"DB lookup failed for {arxiv_id}: {e}")

        # Not in DB, query arXiv API
        return await self._fetch_arxiv_categories(arxiv_id)

    async def _fetch_arxiv_categories(self, arxiv_id: str) -> list[str] | None:
        """Fetch categories from arXiv API.

        Args:
            arxiv_id: arXiv paper ID.

        Returns:
            List of category strings or None if not found.
        """
        import xml.etree.ElementTree as ET
        
        client = get_client()
        url = f"https://export.arxiv.org/api/query?id_list={arxiv_id}"
        
        try:
            response = await client.get(url)
            response.raise_for_status()
            
            # Parse XML
            root = ET.fromstring(response.text)
            ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
            
            entry = root.find("atom:entry", ns)
            if entry is None:
                return None
            
            categories = []
            # Primary category
            primary = entry.find("arxiv:primary_category", ns)
            if primary is not None:
                term = primary.get("term")
                if term:
                    categories.append(term)
            
            # All categories
            for cat in entry.findall("atom:category", ns):
                term = cat.get("term")
                if term and term not in categories:
                    categories.append(term)
            
            return categories if categories else None
            
        except Exception as e:
            logger.warning(f"arXiv API lookup failed for {arxiv_id}: {e}")
            return None

    def _parse_date(self, date_str: str) -> datetime:
        """Parse ISO format date string."""
        if not date_str:
            return datetime.now()
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            return datetime.now()
