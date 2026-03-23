"""
datetime.py — UTC datetime and ISO-8601 string helpers.

All timestamps persisted in SQLite are UTC ISO-8601 strings. This module
centralises conversion between datetime objects and that string format.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def utcnow() -> datetime:
    """Return the current time as a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def utcnow_iso() -> str:
    """Return the current UTC time as an ISO-8601 string (e.g. ``2024-01-15T10:30:00+00:00``)."""
    return utcnow().isoformat()


def parse_iso(value: str) -> datetime:
    """
    Parse an ISO-8601 datetime string into a timezone-aware UTC datetime.

    Parameters
    ----------
    value:
        String produced by :func:`utcnow_iso` or compatible.
    """
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        # Treat naive datetimes as UTC (legacy rows).
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def days_ago(days: int) -> datetime:
    """Return a UTC datetime *days* days in the past."""
    return utcnow() - timedelta(days=days)


def hours_ago(hours: int) -> datetime:
    """Return a UTC datetime *hours* hours in the past."""
    return utcnow() - timedelta(hours=hours)
