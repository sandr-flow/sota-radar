"""Shared HTTP client infrastructure."""

import httpx

# Global singleton client
_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
    """Get or create shared AsyncClient singleton.
    
    Returns:
        httpx.AsyncClient: Shared client instance.
    """
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=60.0)
    return _client


async def close_client():
    """Close shared AsyncClient if exists."""
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None
