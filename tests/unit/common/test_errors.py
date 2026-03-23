"""Unit tests for the common.errors module."""

from __future__ import annotations

import pytest

from ssh_discovery.common.errors import DiscoveryError, SshDiscoveryError, TransportError


class TestHierarchy:
    def test_transport_error_is_ssh_discovery_error(self):
        assert issubclass(TransportError, SshDiscoveryError)

    def test_discovery_error_is_ssh_discovery_error(self):
        assert issubclass(DiscoveryError, SshDiscoveryError)


class TestRaising:
    def test_transport_error(self):
        with pytest.raises(TransportError, match="network down"):
            raise TransportError("network down")

    def test_discovery_error(self):
        with pytest.raises(DiscoveryError, match="bad state"):
            raise DiscoveryError("bad state")
