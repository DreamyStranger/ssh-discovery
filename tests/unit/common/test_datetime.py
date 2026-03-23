"""Unit tests for common.datetime module."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ssh_discovery.common.datetime import (
    days_ago,
    hours_ago,
    parse_iso,
    utcnow,
    utcnow_iso,
)


class TestUtcnow:
    def test_returns_timezone_aware_datetime(self):
        dt = utcnow()
        assert dt.tzinfo is not None
        assert dt.tzinfo == timezone.utc

    def test_is_recent(self):
        dt = utcnow()
        assert abs((dt - datetime.now(timezone.utc)).total_seconds()) < 1


class TestUtcnowIso:
    def test_returns_string(self):
        assert isinstance(utcnow_iso(), str)

    def test_parseable_as_iso(self):
        s = utcnow_iso()
        dt = datetime.fromisoformat(s)
        assert dt.tzinfo is not None

    def test_contains_utc_offset(self):
        s = utcnow_iso()
        assert "+00:00" in s


class TestParseIso:
    def test_round_trips_utcnow_iso(self):
        s = utcnow_iso()
        dt = parse_iso(s)
        assert isinstance(dt, datetime)
        assert dt.tzinfo == timezone.utc

    def test_naive_datetime_treated_as_utc(self):
        naive = "2024-01-15T10:30:00"
        dt = parse_iso(naive)
        assert dt.tzinfo == timezone.utc
        assert dt.hour == 10

    def test_aware_datetime_preserved(self):
        aware = "2024-01-15T10:30:00+00:00"
        dt = parse_iso(aware)
        assert dt.tzinfo is not None
        assert dt.year == 2024 and dt.month == 1 and dt.day == 15


class TestDaysAgo:
    def test_returns_datetime_in_the_past(self):
        result = days_ago(1)
        assert result < datetime.now(timezone.utc)

    def test_approximately_correct_offset(self):
        result = days_ago(2)
        expected = datetime.now(timezone.utc) - timedelta(days=2)
        assert abs((result - expected).total_seconds()) < 5

    def test_is_timezone_aware(self):
        assert days_ago(1).tzinfo is not None


class TestHoursAgo:
    def test_returns_datetime_in_the_past(self):
        result = hours_ago(1)
        assert result < datetime.now(timezone.utc)

    def test_approximately_correct_offset(self):
        result = hours_ago(3)
        expected = datetime.now(timezone.utc) - timedelta(hours=3)
        assert abs((result - expected).total_seconds()) < 5

    def test_is_timezone_aware(self):
        assert hours_ago(1).tzinfo is not None
