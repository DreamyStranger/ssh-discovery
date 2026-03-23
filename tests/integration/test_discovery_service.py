"""Integration tests for DiscoveryService."""

from __future__ import annotations

import stat
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from ssh_discovery import DiscoveryConfig, DiscoveryService, SshConfig, TransportError
from ssh_discovery.models import RemoteEntry


def _make_config(mode: str = "directories") -> DiscoveryConfig:
    return DiscoveryConfig(
        ssh=SshConfig(host="localhost", private_key_path="~/.ssh/id_ed25519"),
        remote_path="/var/log/test",
        file_glob="*.log" if mode != "directories" else "*",
        mode=mode,  # type: ignore[arg-type]
    )


def _remote_entry(
    name: str,
    mtime: datetime,
    path: str | None = None,
    mode: int | None = None,
) -> RemoteEntry:
    return RemoteEntry(
        name=name,
        path=path or f"/var/log/test/{name}",
        mtime=mtime,
        mode=mode if mode is not None else stat.S_IFREG | 0o644,
    )


def _run_service(entries: list[RemoteEntry], mode: str = "directories") -> list[RemoteEntry]:
    config = _make_config(mode)
    mock_sftp = MagicMock()
    mock_ssh = MagicMock()
    mock_ssh.__enter__ = MagicMock(return_value=mock_ssh)
    mock_ssh.__exit__ = MagicMock(return_value=False)
    mock_ssh.open_sftp.return_value = mock_sftp

    with (
        patch("ssh_discovery.service.open_ssh_connection", return_value=mock_ssh),
        patch("ssh_discovery.service.list_remote_entries", return_value=entries),
    ):
        return DiscoveryService(config).run()


def _run_service_with_anchor(
    entries: list[RemoteEntry],
    anchor_mtime: datetime,
    anchor_path: str,
    mode: str = "directories",
) -> list[RemoteEntry]:
    config = DiscoveryConfig(
        ssh=SshConfig(host="localhost", private_key_path="~/.ssh/id_ed25519"),
        remote_path="/var/log/test",
        file_glob="*.log" if mode != "directories" else "*",
        mode=mode,  # type: ignore[arg-type]
        anchor_mtime=anchor_mtime,
        anchor_path=anchor_path,
    )
    mock_sftp = MagicMock()
    mock_ssh = MagicMock()
    mock_ssh.__enter__ = MagicMock(return_value=mock_ssh)
    mock_ssh.__exit__ = MagicMock(return_value=False)
    mock_ssh.open_sftp.return_value = mock_sftp

    with (
        patch("ssh_discovery.service.open_ssh_connection", return_value=mock_ssh),
        patch("ssh_discovery.service.list_remote_entries", return_value=entries),
    ):
        return DiscoveryService(config).run()


class TestDiscoveryServiceIntegration:
    def test_returns_all_remote_entries(self):
        remote_entries = [
            _remote_entry("a.log", datetime(2024, 6, 1, tzinfo=timezone.utc)),
            _remote_entry("b.log", datetime(2024, 6, 2, tzinfo=timezone.utc)),
        ]
        result = _run_service(remote_entries, mode="files")
        assert result == remote_entries

    def test_results_are_sorted_by_mtime_then_path(self):
        result = _run_service(
            [
                _remote_entry("b.log", datetime(2024, 6, 2, tzinfo=timezone.utc), "/b/path.log"),
                _remote_entry("a.log", datetime(2024, 6, 1, tzinfo=timezone.utc), "/a/path.log"),
                _remote_entry("c.log", datetime(2024, 6, 2, tzinfo=timezone.utc), "/a/other.log"),
            ],
            mode="files",
        )
        assert [entry.path for entry in result] == ["/a/path.log", "/a/other.log", "/b/path.log"]

    def test_anchor_tuple_filters_out_older_and_equal_entries(self):
        anchor_mtime = datetime(2024, 6, 2, tzinfo=timezone.utc)
        result = _run_service_with_anchor(
            [
                _remote_entry("old.log", datetime(2024, 6, 1, tzinfo=timezone.utc)),
                _remote_entry(
                    "equal.log",
                    datetime(2024, 6, 2, tzinfo=timezone.utc),
                    "/var/log/test/equal.log",
                ),
                _remote_entry("new.log", datetime(2024, 6, 3, tzinfo=timezone.utc)),
            ],
            anchor_mtime=anchor_mtime,
            anchor_path="/var/log/test/equal.log",
            mode="files",
        )
        assert [entry.name for entry in result] == ["new.log"]

    def test_anchor_tuple_allows_same_mtime_but_lexicographically_newer_path(self):
        anchor_mtime = datetime(2024, 6, 2, tzinfo=timezone.utc)
        result = _run_service_with_anchor(
            [
                _remote_entry(
                    "before.log",
                    datetime(2024, 6, 2, tzinfo=timezone.utc),
                    "/var/log/test/a.log",
                ),
                _remote_entry(
                    "anchor.log",
                    datetime(2024, 6, 2, tzinfo=timezone.utc),
                    "/var/log/test/b.log",
                ),
                _remote_entry(
                    "after.log",
                    datetime(2024, 6, 2, tzinfo=timezone.utc),
                    "/var/log/test/c.log",
                ),
            ],
            anchor_mtime=anchor_mtime,
            anchor_path="/var/log/test/b.log",
            mode="files",
        )
        assert [entry.path for entry in result] == ["/var/log/test/c.log"]

    def test_sftp_open_failure_is_wrapped_as_transport_error(self):
        config = _make_config()
        mock_ssh = MagicMock()
        mock_ssh.__enter__ = MagicMock(return_value=mock_ssh)
        mock_ssh.__exit__ = MagicMock(return_value=False)
        mock_ssh.open_sftp.side_effect = OSError("subsystem unavailable")

        with patch("ssh_discovery.service.open_ssh_connection", return_value=mock_ssh):
            with pytest.raises(TransportError, match="Failed to open SFTP session"):
                DiscoveryService(config).run()
