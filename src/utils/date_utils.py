"""Date handling utilities."""

from datetime import datetime, timezone


def parse_iso_date(date_str: str | None) -> datetime:
    """Parse ISO format date string into naive UTC datetime.
    
    Args:
        date_str: ISO date string (e.g. "2023-01-01T12:00:00Z").
        
    Returns:
        Naive datetime object in UTC. Returns datetime.min if input is invalid,
        so papers with missing dates sort last (oldest) rather than newest.
    """
    if not date_str:
        return datetime.min
    
    try:
        # Handle Z suffix
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        # Convert to UTC and remove timezone info (for SQLite compatibility)
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    except ValueError:
        return datetime.min

