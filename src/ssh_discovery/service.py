"""
service.py - Discovery service.

Defines :class:`DiscoveryService`, the main public entry point for
executing one remote discovery cycle.
"""

from __future__ import annotations

import logging

from ssh_discovery.common.errors import TransportError
from ssh_discovery.config import DiscoveryConfig
from ssh_discovery.models import RemoteEntry
from ssh_discovery.transport.sftp_listing import list_remote_entries
from ssh_discovery.transport.ssh_client import open_ssh_connection

logger = logging.getLogger(__name__)


class DiscoveryService:
    """Executes discovery cycles against a configured remote host."""

    def __init__(self, config: DiscoveryConfig) -> None:
        self._config = config

    def run(self) -> list[RemoteEntry]:
        """List matching remote entries and return them.

        The returned items are sorted by ``(mtime, path)`` for deterministic
        downstream processing.
        """
        with open_ssh_connection(self._config.ssh) as ssh:
            try:
                sftp = ssh.open_sftp()
            except Exception as exc:
                message = f"Failed to open SFTP session for {self._config.ssh.host}: {exc}"
                raise TransportError(message) from exc
            try:
                remote_entries = list_remote_entries(
                    sftp=sftp,
                    remote_path=self._config.remote_path,
                    file_glob=self._config.file_glob,
                    mode=self._config.mode,
                )
            finally:
                sftp.close()

        remote_entries.sort(key=lambda remote_entry: (remote_entry.mtime, remote_entry.path))

        if self._config.anchor_mtime is not None and self._config.anchor_path is not None:
            anchor_key = (self._config.anchor_mtime, self._config.anchor_path)
            remote_entries = [
                remote_entry
                for remote_entry in remote_entries
                if (remote_entry.mtime, remote_entry.path) > anchor_key
            ]
            logger.info(
                "Remote listing after anchor filter: %d entr(y/ies) newer than (%s, %s).",
                len(remote_entries),
                anchor_key[0].isoformat(),
                anchor_key[1],
            )
        else:
            logger.info("Remote listing: %d entr(y/ies) found.", len(remote_entries))

        return remote_entries
