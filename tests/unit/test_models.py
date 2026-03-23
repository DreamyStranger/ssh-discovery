"""Unit tests for the top-level models module."""

from __future__ import annotations

import stat
from datetime import datetime, timezone

import pytest

from ssh_discovery.models import RemoteEntry

_MTIME = datetime(2024, 1, 15, tzinfo=timezone.utc)


class TestRemoteEntry:
    def test_fields_are_stored(self):
        entry = RemoteEntry(
            name="app-2024-01-15.log",
            path="/var/log/app-2024-01-15.log",
            mtime=_MTIME,
            mode=stat.S_IFREG | 0o644,
        )
        assert entry.name == "app-2024-01-15.log"
        assert entry.path == "/var/log/app-2024-01-15.log"
        assert entry.mtime == _MTIME

    def test_is_file_property(self):
        entry = RemoteEntry("file.log", "/logs/file.log", _MTIME, stat.S_IFREG | 0o644)
        assert entry.is_file is True
        assert entry.is_dir is False

    def test_is_dir_property(self):
        entry = RemoteEntry("session", "/logs/session", _MTIME, stat.S_IFDIR | 0o755)
        assert entry.is_dir is True
        assert entry.is_file is False

    def test_is_symlink_property(self):
        entry = RemoteEntry("link", "/logs/link", _MTIME, stat.S_IFLNK | 0o777)
        assert entry.is_symlink is True

    def test_none_mode_returns_false_properties(self):
        entry = RemoteEntry("unknown", "/logs/unknown", _MTIME, None)
        assert entry.is_file is False
        assert entry.is_dir is False
        assert entry.is_symlink is False

    def test_is_immutable(self):
        entry = RemoteEntry("f.log", "/f.log", _MTIME, stat.S_IFREG | 0o644)
        with pytest.raises((AttributeError, TypeError)):
            entry.name = "other.log"  # type: ignore[misc]
