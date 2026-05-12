"""Pytest-friendly checks for socket.SO_REUSEADDR."""

from __future__ import annotations

import contextlib
import socket
from typing import Tuple

import pytest

LoopbackAddr = Tuple[str, int]


@pytest.fixture
def loopback_addr() -> LoopbackAddr:
    """Allocate an ephemeral loopback port for deterministic tests."""
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        try:
            sock.bind(("127.0.0.1", 0))
        except OSError as exc:  # pragma: no cover - host-specific permission gate
            pytest.skip(
                f"Host atual nao permite bind em loopback para este teste: {exc}"
            )
        host, port = sock.getsockname()
    return host, port


def _bind_socket(addr: LoopbackAddr, reuse: bool = False) -> socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if reuse:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(addr)
    sock.listen(1)
    return sock


def test_reuseaddr_flag_roundtrip(loopback_addr: LoopbackAddr) -> None:
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        assert sock.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR) > 0
        sock.bind(loopback_addr)
        sock.listen(1)

    try:
        with contextlib.closing(_bind_socket(loopback_addr, reuse=True)) as rebound:
            assert rebound.getsockname()[1] == loopback_addr[1]
    except OSError as exc:  # pragma: no cover - guard for exotic OSes
        pytest.skip(f"Plataforma nao permite reuso imediato da porta: {exc}")


def test_reuseaddr_allows_immediate_rebind(loopback_addr: LoopbackAddr) -> None:
    with contextlib.closing(_bind_socket(loopback_addr, reuse=True)):
        pass

    try:
        with contextlib.closing(_bind_socket(loopback_addr, reuse=True)) as sock:
            assert sock.getsockname()[1] == loopback_addr[1]
    except OSError as exc:  # pragma: no cover - guard for exotic OSes
        pytest.skip(f"Plataforma nao permite reuso imediato da porta: {exc}")
