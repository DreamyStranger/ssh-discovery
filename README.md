# ssh-discovery

[![CI](https://github.com/DreamyStranger/ssh-discovery/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/DreamyStranger/ssh-discovery/actions/workflows/ci.yml?query=branch%3Amaster)
[![PyPI version](https://img.shields.io/pypi/v/ssh-discovery.svg)](https://pypi.org/project/ssh-discovery/)
[![Tested with pytest](https://img.shields.io/badge/tested%20with-pytest-0A9EDC.svg)](https://pytest.org/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Python library for discovering remote filesystem entries over SSH/SFTP.

## Overview

`ssh-discovery` connects to a remote host over SSH/SFTP, scans a path for
matching entries, and returns their metadata as typed Python objects. It
supports three discovery modes and optional incremental discovery via an
anchor checkpoint.

## Discovery modes

| Mode | What it returns |
|---|---|
| `"directories"` | Immediate subdirectories of `remote_path` matching `file_glob` |
| `"files"` | Immediate files in `remote_path` matching `file_glob` |
| `"files_recursive"` | All files under `remote_path` (depth-first), matching `file_glob` |

All results are sorted by `(mtime, path)` for deterministic downstream
processing. Pass an anchor to receive only entries newer than a known
checkpoint — useful for polling workflows that track the last-processed entry.

## Architecture

```text
ssh_discovery/
|- __init__.py       Public API re-exports
|- service.py        DiscoveryService — main entry point
|- config.py         Typed config dataclasses
|- models.py         Shared domain models
|- transport/        SSH/SFTP connectivity and remote entry listing
\- common/           Shared errors and helper utilities
```

### Data flow per `DiscoveryService.run()` call

1. Open SSH connection.
2. Open SFTP session.
3. List remote entries matching `mode` and `file_glob`.
4. Sort results by `(mtime, path)`.
5. Drop entries not newer than the anchor tuple (if configured).
6. Return `list[RemoteEntry]`.

## Installation

```bash
pip install ssh-discovery
```

Or from source:

```bash
git clone https://github.com/DreamyStranger/ssh-discovery.git
cd ssh-discovery
pip install -e ".[dev]"
```

Requirements: Python 3.11+ and Paramiko.

## Usage

### Basic

```python
from ssh_discovery import DiscoveryConfig, DiscoveryService, SshConfig

config = DiscoveryConfig(
    ssh=SshConfig(
        host="192.168.1.100",
        username="logsync",
        private_key_path="/path/to/id_ed25519",
    ),
    remote_path="/var/log/mylogs",
    file_glob="*.log",
    mode="files_recursive",
)

entries = DiscoveryService(config).run()

for entry in entries:
    print(entry.path, entry.mtime, entry.size)
```

### Choosing a mode

```python
# Immediate subdirectories only
config = DiscoveryConfig(ssh=ssh, remote_path="/data", mode="directories")

# Immediate files only
config = DiscoveryConfig(ssh=ssh, remote_path="/data/logs", mode="files", file_glob="*.log")

# All files under the path, any depth
config = DiscoveryConfig(ssh=ssh, remote_path="/data", mode="files_recursive", file_glob="*.gz")
```

### Incremental discovery

Pass the `(mtime, path)` of the last-processed entry to receive only newer
results on the next run:

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

`anchor_mtime` and `anchor_path` must always be provided together.
`anchor_mtime` must be timezone-aware.

### Error handling

```python
from ssh_discovery import DiscoveryError, SshDiscoveryError, TransportError

try:
    entries = DiscoveryService(config).run()
except TransportError as exc:
    # SSH connection failed, auth rejected, SFTP session error, or listing failure
    logger.error("Transport failure: %s", exc)
except DiscoveryError as exc:
    # Unrecoverable error in the discovery workflow
    logger.error("Discovery failure: %s", exc)
except SshDiscoveryError as exc:
    # Catch-all for any ssh-discovery exception
    logger.error("Unexpected failure: %s", exc)
```

### Logging

This package uses standard Python module loggers and does not configure
handlers or formatters. Configure logging in your application before calling
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
| `host` | `str` | — | IP or hostname of the remote host |
| `port` | `int` | `22` | SSH port (1–65535) |
| `username` | `str` | `"logsync"` | SSH username |
| `private_key_path` | `str \| None` | `None` | Path to private key file |
| `password` | `str \| None` | `None` | Password auth, or passphrase for an encrypted key |
| `connect_timeout_seconds` | `float` | `30.0` | TCP, banner, and auth timeout |
| `keepalive_seconds` | `int` | `60` | SSH keepalive interval; `0` disables |
| `known_hosts_path` | `str \| None` | `None` | Path to a custom known_hosts file |
| `allow_unknown_hosts` | `bool` | `False` | Auto-accept unknown host keys (not for production) |

At least one of `private_key_path` or `password` is required.
Unknown SSH host keys are rejected by default. Provide `known_hosts_path` for
strict verification against a pre-populated file, or set `allow_unknown_hosts=True`
only in controlled environments.

### `DiscoveryConfig`

| Field | Type | Default | Description |
|---|---|---|---|
| `ssh` | `SshConfig` | — | SSH connection settings |
| `remote_path` | `str` | — | Base path on the remote host to scan |
| `file_glob` | `str` | `"*"` | fnmatch glob pattern applied to entry names |
| `mode` | `"directories" \| "files" \| "files_recursive"` | `"directories"` | See [Discovery modes](#discovery-modes) |
| `anchor_mtime` | `datetime \| None` | `None` | Timezone-aware anchor timestamp for incremental discovery |
| `anchor_path` | `str \| None` | `None` | Anchor path tiebreaker; required when `anchor_mtime` is set |

### `RemoteEntry`

Each discovered entry is returned as a `RemoteEntry` frozen dataclass.

| Field / Property | Type | Description |
|---|---|---|
| `name` | `str` | Filename or directory name |
| `path` | `str` | Full remote path |
| `mtime` | `datetime` | Modification time (timezone-aware UTC) |
| `mode` | `int \| None` | Unix stat mode bits; `None` if unavailable |
| `is_file` | `bool` | True if entry is a regular file |
| `is_dir` | `bool` | True if entry is a directory |
| `is_symlink` | `bool` | True if entry is a symlink |

## Running tests

```bash
pytest
pytest --cov=ssh_discovery --cov-report=term-missing
```

## Notes

- Results are always sorted by `(mtime, path)` — stable and deterministic across runs.
- When an anchor is set, only entries with `(mtime, path) > (anchor_mtime, anchor_path)` are returned.
- `file_glob` uses fnmatch syntax and is applied to entry names, not full paths.
- Persistence, scheduling, and orchestration are intentionally out of scope for this library.
- SSH key authentication is recommended over passwords for production deployments.
