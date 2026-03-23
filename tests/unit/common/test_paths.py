"""Unit tests for common.paths module."""

from __future__ import annotations

import os
from pathlib import Path

from ssh_discovery.common.paths import resolve_path


class TestResolvePath:
    def test_returns_path_object(self):
        result = resolve_path("/tmp/test")
        assert isinstance(result, Path)

    def test_returns_absolute_path(self, tmp_path):
        result = resolve_path(str(tmp_path / "file.db"))
        assert result.is_absolute()

    def test_expands_home_tilde(self):
        result = resolve_path("~/somefile")
        assert "~" not in str(result)
        assert result.is_absolute()

    def test_resolves_relative_segments(self, tmp_path):
        # /tmp/x/../y should resolve to /tmp/y
        raw = str(tmp_path) + "/subdir/../file.db"
        result = resolve_path(raw)
        assert ".." not in str(result)

    def test_expands_environment_variables(self, tmp_path, monkeypatch):
        monkeypatch.setenv("LOGSYNC_TEST_ROOT", str(tmp_path))
        env_expr = "%LOGSYNC_TEST_ROOT%" if os.name == "nt" else "$LOGSYNC_TEST_ROOT"

        result = resolve_path(f"{env_expr}/nested/file.db")

        assert result == (tmp_path / "nested" / "file.db").resolve()
