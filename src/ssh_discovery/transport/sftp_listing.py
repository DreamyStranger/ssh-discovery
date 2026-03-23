"""
sftp_listing.py - Remote entry listing via SFTP.

Lists remote filesystem entries in a configured path over an open SFTP session
and returns typed :class:`~ssh_discovery.models.RemoteEntry` entries.
"""

from __future__ import annotations

import logging
import stat
from datetime import datetime, timezone
from fnmatch import fnmatch

import paramiko

from ssh_discovery.common.errors import TransportError
from ssh_discovery.config import DiscoveryMode
from ssh_discovery.models import RemoteEntry

logger = logging.getLogger(__name__)


def list_remote_entries(
    sftp: paramiko.SFTPClient,
    remote_path: str,
    file_glob: str = "*",
    mode: DiscoveryMode = "directories",
) -> list[RemoteEntry]:
    """List remote entries according to the configured discovery mode."""
    logger.debug(
        "Listing remote path: %s (glob=%s, mode=%s)",
        remote_path,
        file_glob,
        mode,
    )

    try:
        if mode == "files_recursive":
            entries = _list_recursive_files(sftp, remote_path, file_glob)
        else:
            entries = _list_immediate_entries(sftp, remote_path, file_glob, mode)
    except OSError as exc:
        raise TransportError(f"Failed to list remote path {remote_path!r}: {exc}") from exc

    logger.debug("Found %d matching entries in %s.", len(entries), remote_path)
    return entries


def _list_immediate_entries(
    sftp: paramiko.SFTPClient,
    remote_path: str,
    file_glob: str,
    mode: DiscoveryMode,
) -> list[RemoteEntry]:
    entries = sftp.listdir_attr(remote_path)
    remote_entries: list[RemoteEntry] = []

    for attr in entries:
        name = attr.filename
        if not name or not fnmatch(name, file_glob):
            continue
        if attr.st_mode is None:
            _log_missing_mode(attr)
            continue

        is_dir = stat.S_ISDIR(attr.st_mode)
        is_file = stat.S_ISREG(attr.st_mode)
        if mode == "directories" and not is_dir:
            continue
        if mode == "files" and not is_file:
            continue

        remote_entries.append(_to_remote_entry(remote_path, attr))

    return remote_entries


def _list_recursive_files(
    sftp: paramiko.SFTPClient,
    remote_path: str,
    file_glob: str,
) -> list[RemoteEntry]:
    remote_entries: list[RemoteEntry] = []
    stack = [remote_path.rstrip("/")]

    while stack:
        current_path = stack.pop()
        for attr in sftp.listdir_attr(current_path):
            name = attr.filename
            if not name:
                continue
            if attr.st_mode is None:
                _log_missing_mode(attr)
                continue

            child_path = f"{current_path.rstrip('/')}/{name}"
            if stat.S_ISDIR(attr.st_mode):
                stack.append(child_path)
                continue
            if stat.S_ISREG(attr.st_mode) and fnmatch(name, file_glob):
                remote_entries.append(_to_remote_entry(current_path, attr))

    return remote_entries


def _to_remote_entry(parent_path: str, attr: paramiko.SFTPAttributes) -> RemoteEntry:
    return RemoteEntry(
        name=attr.filename,
        path=f"{parent_path.rstrip('/')}/{attr.filename}",
        mtime=datetime.fromtimestamp(attr.st_mtime or 0, tz=timezone.utc),
        mode=attr.st_mode,
    )


def _log_missing_mode(attr: paramiko.SFTPAttributes) -> None:
    logger.warning(
        "SFTP entry %r has no st_mode - skipping. "
        "If the remote directory appears incomplete, the SFTP server may not report file modes.",
        attr.filename,
    )
