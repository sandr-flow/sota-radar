"""arXiv source implementation for sota-radar."""

import xml.etree.ElementTree as ET
from datetime import datetime

import httpx

from src.infrastructure.http_client import get_client
from src.models.paper import Paper
from src.sources.base import BaseSource
from src.utils.date_utils import parse_iso_date

# arXiv API constants
ARXIV_API_URL = "https://export.arxiv.org/api/query"
ARXIV_NS = {"atom": "http://www.w3.org/2005/Atom"}


class ArxivSource(BaseSource):
    """arXiv paper source implementation.

    Fetches papers from arXiv API using their Atom feed.
    """

    @property
    def source_name(self) -> str:
        """Return source identifier."""
        return "arxiv"

    async def fetch_papers(
        self,
        category: str | None = None,
        search_query: str | None = None,
        max_results: int = 100,
    ) -> list[Paper]:
        """Fetch papers from arXiv.

        Args:
            category: arXiv category (e.g., "cs.LG", "cs.CL").
            search_query: Custom search query.
            max_results: Maximum number of results to return.

        Returns:
            List of Paper objects.
        """
        query = self._build_query(category, search_query)
        params = {
            "search_query": query,
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }

        client = get_client()
        response = await client.get(ARXIV_API_URL, params=params)
        response.raise_for_status()

        return self._parse_response(response.text)

    def _build_query(
        self, category: str | None, search_query: str | None
    ) -> str:
        """Build arXiv API query string."""
        if search_query:
            return search_query
        if category:
            return f"cat:{category}"
        return "cat:cs.LG"  # Default fallback

    def _parse_response(self, xml_content: str) -> list[Paper]:
        """Parse arXiv Atom feed response into Paper objects."""
        root = ET.fromstring(xml_content)
        papers = []

        for entry in root.findall("atom:entry", ARXIV_NS):
            paper = self._parse_entry(entry)
            if paper:
                papers.append(paper)

        return papers

    def _parse_entry(self, entry: ET.Element) -> Paper | None:
        """Parse single Atom entry into Paper object."""
        try:
            # Extract ID (format: http://arxiv.org/abs/2301.12345v1)
            id_elem = entry.find("atom:id", ARXIV_NS)
            if id_elem is None or id_elem.text is None:
                return None
            arxiv_id = id_elem.text.split("/abs/")[-1]

            # Extract title
            title_elem = entry.find("atom:title", ARXIV_NS)
            title = self._clean_text(title_elem.text if title_elem is not None else "")

            # Extract abstract
            summary_elem = entry.find("atom:summary", ARXIV_NS)
            abstract = self._clean_text(
                summary_elem.text if summary_elem is not None else ""
            )

            # Extract authors
            authors = []
            for author in entry.findall("atom:author", ARXIV_NS):
                name_elem = author.find("atom:name", ARXIV_NS)
                if name_elem is not None and name_elem.text:
                    authors.append(name_elem.text)

            # Extract published date
            published_elem = entry.find("atom:published", ARXIV_NS)
            published_str = (
                published_elem.text if published_elem is not None else None
            )
            published = parse_iso_date(published_str)

            # Extract URLs
            url = f"https://arxiv.org/abs/{arxiv_id}"
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

            return Paper(
                source=self.source_name,
                source_id=arxiv_id,
                title=title,
                abstract=abstract,
                authors=authors,
                published=published,
                url=url,
                pdf_url=pdf_url,
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to parse arXiv entry: {e}")
            return None

    def _clean_text(self, text: str) -> str:
        """Clean text by removing extra whitespace."""
        return " ".join(text.split())
