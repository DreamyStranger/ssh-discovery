"""Unit tests for transport.ssh_client module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import paramiko
import pytest

from ssh_discovery.common.errors import TransportError
from ssh_discovery.config import SshConfig
from ssh_discovery.transport.ssh_client import _build_connect_kwargs, open_ssh_connection


def _cfg(**kwargs) -> SshConfig:
    defaults = dict(host="192.168.1.1", private_key_path="/keys/id_ed25519")
    defaults.update(kwargs)
    return SshConfig(**defaults)


class TestBuildConnectKwargs:
    def test_basic_fields_are_set(self):
        kwargs = _build_connect_kwargs(_cfg())
        assert kwargs["hostname"] == "192.168.1.1"
        assert kwargs["port"] == 22
        assert kwargs["username"] == "logsync"

    def test_timeout_comes_from_config(self):
        kwargs = _build_connect_kwargs(_cfg(connect_timeout_seconds=15.0))
        assert kwargs["timeout"] == 15.0
        assert kwargs["banner_timeout"] == 15.0
        assert kwargs["auth_timeout"] == 15.0

    def test_private_key_path_is_used(self):
        kwargs = _build_connect_kwargs(_cfg(private_key_path="/keys/id_ed25519"))
        assert "key_filename" in kwargs
        assert "id_ed25519" in kwargs["key_filename"]
        assert "password" not in kwargs
        assert "passphrase" not in kwargs

    def test_password_used_when_no_key(self):
        cfg = SshConfig(host="192.168.1.1", password="s3cr3t")
        kwargs = _build_connect_kwargs(cfg)
        assert kwargs["password"] == "s3cr3t"
        assert kwargs.get("look_for_keys") is False
        assert "key_filename" not in kwargs

    def test_password_is_used_as_passphrase_when_key_is_present(self):
        cfg = SshConfig(
            host="192.168.1.1",
            private_key_path="/keys/id_ed25519",
            password="key-passphrase",
        )
        kwargs = _build_connect_kwargs(cfg)
        assert "key_filename" in kwargs
        assert kwargs["passphrase"] == "key-passphrase"
        assert "password" not in kwargs

    def test_custom_port_is_forwarded(self):
        kwargs = _build_connect_kwargs(_cfg(port=2222))
        assert kwargs["port"] == 2222


class TestOpenSshConnection:
    def test_uses_strict_host_key_verification_when_known_hosts_path_set(self):
        client = MagicMock()
        transport = MagicMock()
        client.get_transport.return_value = transport

        with patch(
            "ssh_discovery.transport.ssh_client.paramiko.SSHClient",
            return_value=client,
        ):
            with open_ssh_connection(
                _cfg(known_hosts_path="/tmp/known_hosts", keepalive_seconds=30)
            ) as returned:
                assert returned is client

        client.load_system_host_keys.assert_called_once_with()
        client.load_host_keys.assert_called_once_with("/tmp/known_hosts")
        policy = client.set_missing_host_key_policy.call_args.args[0]
        assert isinstance(policy, paramiko.RejectPolicy)
        client.connect.assert_called_once()
        transport.set_keepalive.assert_called_once_with(30)
        client.close.assert_called_once()

    def test_uses_strict_policy_without_known_hosts_by_default(self):
        client = MagicMock()
        client.get_transport.return_value = None

        with patch(
            "ssh_discovery.transport.ssh_client.paramiko.SSHClient",
            return_value=client,
        ):
            with open_ssh_connection(_cfg()):
                pass

        client.load_system_host_keys.assert_called_once_with()
        policy = client.set_missing_host_key_policy.call_args.args[0]
        assert isinstance(policy, paramiko.RejectPolicy)
        client.close.assert_called_once()

    def test_uses_auto_add_policy_when_unknown_hosts_are_allowed(self):
        client = MagicMock()
        client.get_transport.return_value = None

        with patch(
            "ssh_discovery.transport.ssh_client.paramiko.SSHClient",
            return_value=client,
        ):
            with open_ssh_connection(_cfg(allow_unknown_hosts=True)):
                pass

        client.load_system_host_keys.assert_called_once_with()
        policy = client.set_missing_host_key_policy.call_args.args[0]
        assert isinstance(policy, paramiko.AutoAddPolicy)
        client.close.assert_called_once()

    def test_authentication_errors_are_wrapped(self):
        client = MagicMock()
        client.connect.side_effect = paramiko.AuthenticationException("bad credentials")

        with patch(
            "ssh_discovery.transport.ssh_client.paramiko.SSHClient",
            return_value=client,
        ):
            with pytest.raises(TransportError, match="authentication failed"):
                with open_ssh_connection(_cfg()):
                    pass

        client.close.assert_called_once()

    def test_ssh_errors_are_wrapped(self):
        client = MagicMock()
        client.connect.side_effect = paramiko.SSHException("handshake failed")

        with patch(
            "ssh_discovery.transport.ssh_client.paramiko.SSHClient",
            return_value=client,
        ):
            with pytest.raises(TransportError, match="SSH error connecting"):
                with open_ssh_connection(_cfg()):
                    pass

        client.close.assert_called_once()

    def test_network_errors_are_wrapped(self):
        client = MagicMock()
        client.connect.side_effect = OSError("timeout")

        with patch(
            "ssh_discovery.transport.ssh_client.paramiko.SSHClient",
            return_value=client,
        ):
            with pytest.raises(TransportError, match="Network error connecting"):
                with open_ssh_connection(_cfg()):
                    pass

        client.close.assert_called_once()
