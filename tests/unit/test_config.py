"""Unit tests for the config module."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from ssh_discovery.config import DiscoveryConfig, SshConfig


class TestSshConfig:
    def test_minimal_valid_with_key(self):
        cfg = SshConfig(host="192.168.1.1", private_key_path="/keys/id_ed25519")
        assert cfg.host == "192.168.1.1"
        assert cfg.port == 22
        assert cfg.username == "logsync"
        assert cfg.allow_unknown_hosts is False

    def test_minimal_valid_with_password(self):
        cfg = SshConfig(host="192.168.1.1", password="secret")
        assert cfg.password == "secret"

    def test_allow_unknown_hosts_can_be_enabled(self):
        cfg = SshConfig(host="h", private_key_path="/k", allow_unknown_hosts=True)
        assert cfg.allow_unknown_hosts is True

    def test_empty_host_raises(self):
        with pytest.raises(ValueError, match="host"):
            SshConfig(host="", private_key_path="/k")

    def test_no_auth_raises(self):
        with pytest.raises(ValueError, match="private_key_path or password"):
            SshConfig(host="192.168.1.1")


class TestDiscoveryConfig:
    def test_valid_config(self):
        cfg = DiscoveryConfig(
            ssh=SshConfig(host="192.168.1.1", private_key_path="/k"),
            remote_path="/var/log/app",
        )
        assert cfg.remote_path == "/var/log/app"
        assert cfg.file_glob == "*"
        assert cfg.mode == "directories"

    def test_custom_glob_and_mode(self):
        cfg = DiscoveryConfig(
            ssh=SshConfig(host="192.168.1.1", private_key_path="/k"),
            remote_path="/logs",
            file_glob="*.jsonl",
            mode="files_recursive",
        )
        assert cfg.file_glob == "*.jsonl"
        assert cfg.mode == "files_recursive"

    def test_anchor_mtime_can_be_set(self):
        cfg = DiscoveryConfig(
            ssh=SshConfig(host="192.168.1.1", private_key_path="/k"),
            remote_path="/logs",
            anchor_mtime=datetime(2024, 1, 1, tzinfo=timezone.utc),
            anchor_path="/logs/anchor.log",
        )
        assert cfg.anchor_mtime == datetime(2024, 1, 1, tzinfo=timezone.utc)
        assert cfg.anchor_path == "/logs/anchor.log"

    def test_empty_path_raises(self):
        with pytest.raises(ValueError, match="remote_path"):
            DiscoveryConfig(
                ssh=SshConfig(host="192.168.1.1", private_key_path="/k"),
                remote_path="",
            )

    def test_invalid_mode_raises(self):
        with pytest.raises(ValueError, match="mode"):
            DiscoveryConfig(
                ssh=SshConfig(host="192.168.1.1", private_key_path="/k"),
                remote_path="/logs",
                mode="bad-mode",  # type: ignore[arg-type]
            )

    def test_naive_anchor_mtime_raises(self):
        with pytest.raises(ValueError, match="timezone-aware"):
            DiscoveryConfig(
                ssh=SshConfig(host="192.168.1.1", private_key_path="/k"),
                remote_path="/logs",
                anchor_mtime=datetime(2024, 1, 1),
                anchor_path="/logs/anchor.log",
            )

    def test_anchor_fields_must_be_provided_together(self):
        with pytest.raises(ValueError, match="provided together"):
            DiscoveryConfig(
                ssh=SshConfig(host="192.168.1.1", private_key_path="/k"),
                remote_path="/logs",
                anchor_mtime=datetime(2024, 1, 1, tzinfo=timezone.utc),
            )

    def test_empty_anchor_path_raises(self):
        with pytest.raises(ValueError, match="anchor_path"):
            DiscoveryConfig(
                ssh=SshConfig(host="192.168.1.1", private_key_path="/k"),
                remote_path="/logs",
                anchor_mtime=datetime(2024, 1, 1, tzinfo=timezone.utc),
                anchor_path="",
            )
