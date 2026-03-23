"""Unit tests for transport.sftp_listing module."""

from __future__ import annotations

import stat
from datetime import timezone
from unittest.mock import MagicMock

import pytest

from ssh_discovery.common.errors import TransportError
from ssh_discovery.models import RemoteEntry
from ssh_discovery.transport.sftp_listing import list_remote_entries

_DEFAULT_MODE = object()


def _make_attr(
    filename: str,
    mtime: int = 1_700_000_000,
    mode: object = _DEFAULT_MODE,
):
    attr = MagicMock()
    attr.filename = filename
    attr.st_mtime = mtime
    attr.st_mode = stat.S_IFDIR | 0o755 if mode is _DEFAULT_MODE else mode
    return attr


def _make_sftp(mapping: dict[str, list] | list) -> MagicMock:
    sftp = MagicMock()
    if isinstance(mapping, list):
        sftp.listdir_attr.return_value = mapping
    else:
        def _listdir_attr(path: str):
            return mapping[path]
        sftp.listdir_attr.side_effect = _listdir_attr
    return sftp


class TestListRemoteEntries:
    def test_returns_remote_entry_objects_for_directories(self):
        sftp = _make_sftp([_make_attr("app-2024-01-15")])
        result = list_remote_entries(sftp, remote_path="/var/log/app")
        assert len(result) == 1
        assert isinstance(result[0], RemoteEntry)
        assert result[0].is_dir is True

    def test_directory_mode_sets_name_and_path(self):
        sftp = _make_sftp([_make_attr("app-2024-01-15")])
        result = list_remote_entries(sftp, remote_path="/var/log/app", mode="directories")
        assert result[0].name == "app-2024-01-15"
        assert result[0].path == "/var/log/app/app-2024-01-15"

    def test_file_mode_returns_regular_files_only(self):
        sftp = _make_sftp(
            [
                _make_attr("app.log", mode=stat.S_IFREG | 0o644),
                _make_attr("nested", mode=stat.S_IFDIR | 0o755),
            ]
        )
        result = list_remote_entries(sftp, remote_path="/logs", mode="files")
        assert [entry.name for entry in result] == ["app.log"]
        assert result[0].is_file is True

    def test_recursive_mode_walks_nested_directories(self):
        sftp = _make_sftp(
            {
                "/logs": [
                    _make_attr("root.log", mode=stat.S_IFREG | 0o644),
                    _make_attr("nested", mode=stat.S_IFDIR | 0o755),
                ],
                "/logs/nested": [
                    _make_attr("child.log", mode=stat.S_IFREG | 0o644),
                    _make_attr("deeper", mode=stat.S_IFDIR | 0o755),
                ],
                "/logs/nested/deeper": [
                    _make_attr("skip.txt", mode=stat.S_IFREG | 0o644),
                    _make_attr("deep.log", mode=stat.S_IFREG | 0o644),
                ],
            }
        )
        result = list_remote_entries(
            sftp,
            remote_path="/logs",
            mode="files_recursive",
            file_glob="*.log",
        )
        assert [entry.path for entry in result] == [
            "/logs/root.log",
            "/logs/nested/child.log",
            "/logs/nested/deeper/deep.log",
        ]

    def test_mtime_is_utc_aware(self):
        sftp = _make_sftp([_make_attr("session-dir", mtime=1_700_000_000)])
        result = list_remote_entries(sftp, remote_path="/logs")
        assert result[0].mtime.tzinfo == timezone.utc

    def test_missing_mtime_defaults_to_epoch(self):
        sftp = _make_sftp([_make_attr("session-dir", mtime=0)])
        result = list_remote_entries(sftp, remote_path="/logs")
        assert result[0].mtime.timestamp() == 0

    def test_glob_filter_excludes_non_matching(self):
        sftp = _make_sftp(
            [
                _make_attr("app-2024-01-15", mode=stat.S_IFDIR | 0o755),
                _make_attr("app-2024-01-16", mode=stat.S_IFDIR | 0o755),
                _make_attr("other-dir", mode=stat.S_IFDIR | 0o755),
            ]
        )
        result = list_remote_entries(sftp, remote_path="/logs", file_glob="app-*")
        names = {entry.name for entry in result}
        assert names == {"app-2024-01-15", "app-2024-01-16"}

    def test_entries_without_mode_are_skipped(self):
        sftp = _make_sftp([_make_attr("unknown", mode=None), _make_attr("known")])
        result = list_remote_entries(sftp, remote_path="/logs")
        assert [entry.name for entry in result] == ["known"]

    def test_empty_directory_returns_empty_list(self):
        sftp = _make_sftp([])
        result = list_remote_entries(sftp, remote_path="/logs")
        assert result == []

    def test_listing_errors_are_wrapped(self):
        sftp = MagicMock()
        sftp.listdir_attr.side_effect = OSError("permission denied")
        with pytest.raises(TransportError, match="Failed to list remote path"):
            list_remote_entries(sftp, remote_path="/logs")
