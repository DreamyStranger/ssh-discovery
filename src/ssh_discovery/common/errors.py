"""
errors.py - Package exception hierarchy.
"""


class SshDiscoveryError(Exception):
    """Base class for all ssh-discovery exceptions."""


LogsyncError = SshDiscoveryError


class TransportError(SshDiscoveryError):
    """Raised when SSH/SFTP communication fails."""


class DiscoveryError(SshDiscoveryError):
    """Raised when the discovery workflow encounters an unrecoverable error."""
