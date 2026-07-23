from __future__ import annotations

import argparse

import pytest

from aura_spatial_cli import _loopback_host, _tcp_port


def test_construction_video_demo_host_is_loopback_only() -> None:
    assert _loopback_host("127.0.0.1") == "127.0.0.1"
    assert _loopback_host("localhost") == "localhost"
    for value in ("0.0.0.0", "::", "192.0.2.1", "example.com"):
        with pytest.raises(argparse.ArgumentTypeError, match="loopback-only"):
            _loopback_host(value)


def test_construction_video_demo_port_is_bounded() -> None:
    assert _tcp_port("1") == 1
    assert _tcp_port("8767") == 8767
    assert _tcp_port("65535") == 65_535
    for value in ("0", "65536", "-1", "not-a-port"):
        with pytest.raises(argparse.ArgumentTypeError):
            _tcp_port(value)
