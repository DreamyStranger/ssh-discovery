"""
models.py - Shared domain models.

Single source of truth for the data classes used across the package.
"""

from __future__ import annotations

import stat
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class RemoteEntry:
    """A filesystem entry discovered on the remote host via SFTP."""

    name: str
    path: str
    mtime: datetime
    mode: int | None

    @property
    def is_dir(self) -> bool:
        return self.mode is not None and stat.S_ISDIR(self.mode)

    @property
    def is_file(self) -> bool:
        return self.mode is not None and stat.S_ISREG(self.mode)

    @property
    def is_symlink(self) -> bool:
        return self.mode is not None and stat.S_ISLNK(self.mode)
