"""
config.py - Typed configuration dataclasses.

Defines :class:`SshConfig` and :class:`DiscoveryConfig`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

DiscoveryMode = Literal["directories", "files", "files_recursive"]


@dataclass(frozen=True)
class SshConfig:
    """SSH/SFTP connection parameters."""

    host: str
    port: int = 22
    username: str = "logsync"
    private_key_path: str | None = None
    password: str | None = None
    known_hosts_path: str | None = None
    allow_unknown_hosts: bool = False
    connect_timeout_seconds: float = 30.0
    keepalive_seconds: int = 60

    def __post_init__(self) -> None:
        if not self.host:
            raise ValueError("SshConfig.host must not be empty")
        if not (self.private_key_path or self.password):
            raise ValueError("SshConfig requires either private_key_path or password")
        if not (1 <= self.port <= 65535):
            raise ValueError(f"SshConfig.port must be 1-65535, got {self.port}")
        if self.connect_timeout_seconds <= 0:
            raise ValueError("SshConfig.connect_timeout_seconds must be > 0")
        if self.keepalive_seconds < 0:
            raise ValueError("SshConfig.keepalive_seconds must be >= 0")


@dataclass(frozen=True)
class DiscoveryConfig:
    """Top-level configuration object for a discovery run."""

    ssh: SshConfig
    remote_path: str
    file_glob: str = "*"
    mode: DiscoveryMode = "directories"
    anchor_mtime: datetime | None = None
    anchor_path: str | None = None

    def __post_init__(self) -> None:
        if not self.remote_path:
            raise ValueError("DiscoveryConfig.remote_path must not be empty")
        if self.mode not in {"directories", "files", "files_recursive"}:
            raise ValueError(
                "DiscoveryConfig.mode must be one of: directories, files, files_recursive"
            )
        if self.anchor_mtime is not None and self.anchor_mtime.tzinfo is None:
            raise ValueError("DiscoveryConfig.anchor_mtime must be timezone-aware")
        if self.anchor_path is not None and not self.anchor_path:
            raise ValueError("DiscoveryConfig.anchor_path must not be empty")
        if (self.anchor_mtime is None) != (self.anchor_path is None):
            raise ValueError(
                "DiscoveryConfig.anchor_mtime and anchor_path must be provided together"
            )
