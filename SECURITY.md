# Security Policy

## Reporting a vulnerability

Please do not open a public GitHub issue for security vulnerabilities.

Report them privately via [GitHub's security advisory feature](https://github.com/DreamyStranger/ssh-discovery/security/advisories/new).

Include a description of the issue, steps to reproduce, and the potential impact.

## Known considerations

- Host key verification: by default, unknown SSH host keys are accepted automatically (`AutoAddPolicy`). For production deployments, set `SshConfig.known_hosts_path` to a pre-populated known_hosts file to enable strict verification (`RejectPolicy`).
- Private key handling: private key paths are passed directly to Paramiko. Ensure key files have appropriate permissions (`chmod 600`).
- SQLite access: the manifest database is shared with other pipeline components. Ensure the database file and its parent directory have appropriate filesystem permissions.
