# ssh-discovery

[![CI](https://github.com/DreamyStranger/ssh-discovery/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/DreamyStranger/ssh-discovery/actions/workflows/ci.yml?query=branch%3Amaster)
[![PyPI version](https://img.shields.io/pypi/v/ssh-discovery.svg)](https://pypi.org/project/ssh-discovery/)
[![Tested with pytest](https://img.shields.io/badge/tested%20with-pytest-0A9EDC.svg)](https://pytest.org/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Python library for discovering remote filesystem entries over SSH/SFTP.

## Overview

`ssh-discovery` connects to a remote host over SSH/SFTP, scans a path for
matching entries, and returns their metadata as Python objects. It can also do
deterministic incremental discovery when the caller provides an anchor tuple.

This package supports:
- immediate directories in a path
- immediate files in a path
- recursive file discovery under a path
- optional incremental discovery using `(anchor_mtime, anchor_path)`

## Architecture

```text
ssh_discovery/
|- __init__.py       Public API re-exports
|- service.py        DiscoveryService - main entry point
|- config.py         Typed config dataclasses
|- models.py         Shared domain models
|- transport/        SSH/SFTP connectivity and remote entry listing
\- common/           Shared errors and helper utilities
```

### Data flow per `DiscoveryService.run()` call

1. Open SSH.
2. Open SFTP.
3. List matching remote entries.
4. Sort results by `(mtime, path)`.
5. Optionally drop entries whose `(mtime, path)` is not newer than the anchor tuple.
6. Return `list[RemoteEntry]`.

## Installation

```bash
pip install ssh-discovery
```

Or from source:

```bash
git clone <repo>
cd ssh-discovery
pip install -e ".[dev]"
```

Requirements: Python 3.11+ and Paramiko.

## Usage

```python
from ssh_discovery import DiscoveryConfig, DiscoveryService, SshConfig

config = DiscoveryConfig(
    ssh=SshConfig(
        host="192.168.1.100",
        port=22,
        username="logsync",
        private_key_path="/path/to/id_ed25519",
        connect_timeout_seconds=10.0,
        keepalive_seconds=30,
    ),
    remote_path="/var/log/mylogs",
    file_glob="*.log",
    mode="files_recursive",
    anchor_mtime=None,  # or a timezone-aware datetime anchor
    anchor_path=None,   # required together with anchor_mtime
)

service = DiscoveryService(config)
remote_entries = service.run()

for entry in remote_entries:
    print(entry.path, entry.mtime, entry.mode, entry.is_file, entry.is_dir)
```

### Incremental discovery

If your orchestrator tracks the last processed entry, pass its `(mtime, path)`
back into the next run:

```python
from datetime import datetime, timezone

config = DiscoveryConfig(
    ssh=SshConfig(
        host="192.168.1.100",
        private_key_path="/path/to/id_ed25519",
    ),
    remote_path="/var/log/mylogs",
    mode="files_recursive",
    anchor_mtime=datetime(2026, 3, 23, 12, 0, tzinfo=timezone.utc),
    anchor_path="/var/log/mylogs/app-2026-03-23.log",
)
```

### Error handling

```python
from ssh_discovery import SshDiscoveryError, TransportError

try:
    remote_entries = service.run()
except TransportError as exc:
    logger.error("Transport failure: %s", exc)
except SshDiscoveryError as exc:
    logger.error("Discovery failure: %s", exc)
```

### Logging

This package uses standard Python module loggers and does not configure handlers
or formatters. Configure logging in your application before calling
`service.run()`.

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
```

## Configuration reference

### `SshConfig`

| Field | Type | Default | Description |
|---|---|---|---|
| `host` | `str` | - | IP or hostname of the remote host |
| `port` | `int` | `22` | SSH port |
| `username` | `str` | `"logsync"` | SSH username |
| `private_key_path` | `str \| None` | `None` | Path to private key file |
| `password` | `str \| None` | `None` | Password auth or private-key passphrase |
| `connect_timeout_seconds` | `float` | `30.0` | TCP, banner, and auth timeout |
| `keepalive_seconds` | `int` | `60` | SSH keepalive interval, `0` disables |
| `known_hosts_path` | `str \| None` | `None` | Known-hosts path for strict verification |
| `allow_unknown_hosts` | `bool` | `False` | Accept unknown host keys automatically |

At least one of `private_key_path` or `password` is required.
Unknown SSH hosts are rejected by default. Set `allow_unknown_hosts=True`
only in controlled environments where trust-on-first-use is acceptable.

### `DiscoveryConfig`

| Field | Type | Default | Description |
|---|---|---|---|
| `ssh` | `SshConfig` | - | SSH connection settings |
| `remote_path` | `str` | - | Remote path to scan |
| `file_glob` | `str` | `"*"` | Glob pattern for matching entry names |
| `mode` | `"directories" \| "files" \| "files_recursive"` | `"directories"` | Discovery behavior |
| `anchor_mtime` | `datetime \| None` | `None` | Anchor timestamp for incremental discovery |
| `anchor_path` | `str \| None` | `None` | Anchor path tiebreaker for incremental discovery |

`anchor_mtime` and `anchor_path` must be provided together.

## Running tests

```bash
pytest
pytest --cov=ssh_discovery --cov-report=term-missing
```

## Notes

- Results are sorted by remote `mtime`, with `path` as a tiebreaker.
- When `anchor_mtime` and `anchor_path` are set, only entries with `(mtime, path)` greater than that tuple are returned.
- Returned `RemoteEntry` objects include `name`, `path`, `mtime`, and raw `mode`.
- Convenience properties `is_dir`, `is_file`, and `is_symlink` are derived from `mode`.
- Persistence and orchestration are intentionally external to the library.
- SSH keys are preferred over passwords for production deployments.
- Unknown SSH host keys are rejected by default unless explicitly allowed.
