"""
ssh_client.py - SSH connection lifecycle.

Provides a context manager that opens and closes an authenticated Paramiko
:class:`~paramiko.client.SSHClient`. Isolates all Paramiko imports and
connection details from the rest of the package.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

import paramiko

from ssh_discovery.common.errors import TransportError
from ssh_discovery.config import SshConfig

logger = logging.getLogger(__name__)


@contextmanager
def open_ssh_connection(config: SshConfig) -> Generator[paramiko.SSHClient, None, None]:
    """Context manager that yields an authenticated :class:`paramiko.SSHClient`.

    Closes the connection on exit, even if an exception is raised.

    Parameters
    ----------
    config:
        SSH connection settings from :class:`~ssh_discovery.config.SshConfig`.

    Raises
    ------
    TransportError
        If the connection or authentication fails.
    """
    client: paramiko.SSHClient | None = None

    try:
        client = paramiko.SSHClient()
        client.load_system_host_keys()

        if config.known_hosts_path:
            host_keys_path = Path(config.known_hosts_path).expanduser()
            client.load_host_keys(str(host_keys_path))
            client.set_missing_host_key_policy(paramiko.RejectPolicy())
            logger.debug("Host key verification enabled (known_hosts=%s).", host_keys_path)
        elif config.allow_unknown_hosts:
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            logger.warning(
                "allow_unknown_hosts=True for %s; "
                "unknown host keys will be accepted automatically.",
                config.host,
            )
        else:
            client.set_missing_host_key_policy(paramiko.RejectPolicy())
            logger.debug("Strict host key verification enabled using system known_hosts.")

        logger.debug("Connecting to %s:%d as %s", config.host, config.port, config.username)

        connect_kwargs = _build_connect_kwargs(config)
        client.connect(**connect_kwargs)
        if config.keepalive_seconds > 0:
            transport = client.get_transport()
            if transport:
                transport.set_keepalive(config.keepalive_seconds)
        logger.debug("SSH connection established.")
        yield client
    except paramiko.AuthenticationException as exc:
        raise TransportError(
            f"SSH authentication failed for {config.username}@{config.host}: {exc}"
        ) from exc
    except paramiko.SSHException as exc:
        raise TransportError(f"SSH error connecting to {config.host}: {exc}") from exc
    except OSError as exc:
        raise TransportError(f"Network error connecting to {config.host}: {exc}") from exc
    finally:
        try:
            if client is not None:
                client.close()
        finally:
            logger.debug("SSH connection closed.")


def _build_connect_kwargs(config: SshConfig) -> dict[str, Any]:
    timeout = config.connect_timeout_seconds
    kwargs: dict[str, Any] = {
        "hostname": config.host,
        "port": config.port,
        "username": config.username,
        "timeout": timeout,
        "banner_timeout": timeout,
        "auth_timeout": timeout,
    }

    if config.private_key_path:
        key_path = Path(config.private_key_path).expanduser()
        logger.debug("Using private key: %s", key_path)
        kwargs["key_filename"] = str(key_path)
        if config.password:
            kwargs["passphrase"] = config.password
    elif config.password:
        kwargs["password"] = config.password
        kwargs["look_for_keys"] = False

    return kwargs
