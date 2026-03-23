"""
paths.py — File system path helpers.

Utilities for resolving and expanding paths, keeping path manipulation
out of business logic modules.
"""

import os
from pathlib import Path


def resolve_path(raw: str) -> Path:
    """Expand ``~`` and environment variables, then return an absolute Path."""
    expanded = os.path.expandvars(raw)
    return Path(expanded).expanduser().resolve()
