# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.2]

### Added

- General-purpose remote entry discovery over SSH/SFTP.
- Discovery modes for immediate directories, immediate files, and recursive files.
- `RemoteEntry` model with `name`, `path`, `mtime`, `mode`, and convenience
  properties such as `is_dir`, `is_file`, and `is_symlink`.
- Deterministic incremental discovery using the `(anchor_mtime, anchor_path)`
  tuple.
- Strict-by-default SSH host verification with optional `allow_unknown_hosts`.
- Password authentication and encrypted private-key passphrase support.
- CI, packaging, typed public API, and PyPI-ready project metadata.
