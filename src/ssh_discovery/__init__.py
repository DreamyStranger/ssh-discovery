"""
ssh_discovery
=============
Discovery library for remote log workflows over SSH/SFTP.

Connects to a remote host over SSH/SFTP and lists matching remote log
entries. Persistence and workflow orchestration are the responsibility of the
consuming application.
"""

from ssh_discovery.common.errors import (
    DiscoveryError,
    LogsyncError,
    SshDiscoveryError,
    TransportError,
)
from ssh_discovery.config import DiscoveryConfig, DiscoveryMode, SshConfig
from ssh_discovery.models import RemoteEntry
from ssh_discovery.service import DiscoveryService
from ssh_discovery.version import __version__

__all__ = [
    "DiscoveryService",
    "DiscoveryConfig",
    "DiscoveryMode",
    "SshConfig",
    "RemoteEntry",
    "SshDiscoveryError",
    "LogsyncError",
    "DiscoveryError",
    "TransportError",
    "__version__",
]
