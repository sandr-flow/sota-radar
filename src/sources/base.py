"""Base source interface for sota-radar."""

from abc import ABC, abstractmethod

from src.models.paper import Paper


class BaseSource(ABC):
    """Abstract base class for paper sources.

    All source implementations must inherit from this class and implement
    the required methods.
    """

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return unique identifier for this source."""
        pass

    @abstractmethod
    async def fetch_papers(self, **kwargs) -> list[Paper]:
        """Fetch papers from this source.

        Args:
            **kwargs: Source-specific filter parameters.

        Returns:
            List of Paper objects.
        """
        pass
