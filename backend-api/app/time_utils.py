from __future__ import annotations

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return current UTC time as naive datetime for DB/schema compatibility."""
    return datetime.now(UTC).replace(tzinfo=None)
