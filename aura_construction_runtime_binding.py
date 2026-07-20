"""Process-local canonical issuance binding for Construction runtime packets.

The Spatial Construction API is typed and same-process. This registry binds an
immutable packet digest to the exact canonical Construction adapter invocation
that issued it. Serialized copies remain valid in that process, while modified
or independently recomputed packets fail closed before projection.
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Mapping
from functools import wraps
import threading
from typing import Any

from aura_event_contracts import stable_digest

CONSTRUCTION_RUNTIME_BINDING_VERSION = "AURA_CONSTRUCTION_RUNTIME_BINDING_V1"
MAX_CANONICAL_CONSTRUCTION_RUNTIME_PACKETS = 256

_LOCK = threading.RLock()
_ISSUED_PACKETS: OrderedDict[str, str] = OrderedDict()


def register_construction_runtime_packet(
    packet: Mapping[str, Any],
    *,
    state_digest: str,
) -> str:
    """Register one packet emitted by the canonical Construction adapter."""

    if not isinstance(packet, Mapping):
        raise ValueError("Construction runtime packet must be a mapping")
    state = str(state_digest or "").strip()
    if not state:
        raise ValueError("Construction runtime packet state digest must not be empty")
    packet_digest = stable_digest(dict(packet), digest_size=32)
    with _LOCK:
        _ISSUED_PACKETS[packet_digest] = state
        _ISSUED_PACKETS.move_to_end(packet_digest)
        while len(_ISSUED_PACKETS) > MAX_CANONICAL_CONSTRUCTION_RUNTIME_PACKETS:
            _ISSUED_PACKETS.popitem(last=False)
    return packet_digest


def require_canonical_construction_runtime_packet(
    packet: Mapping[str, Any],
    *,
    state_digest: str,
) -> str:
    """Require an exact packet previously issued for the supplied canonical state."""

    if not isinstance(packet, Mapping):
        raise ValueError("Construction runtime packet must be a mapping")
    state = str(state_digest or "").strip()
    packet_digest = stable_digest(dict(packet), digest_size=32)
    with _LOCK:
        issued_state = _ISSUED_PACKETS.get(packet_digest)
    if issued_state != state:
        raise ValueError(
            "Construction runtime packet was not issued by the canonical Construction adapter "
            "for the supplied state"
        )
    return packet_digest


def install_construction_runtime_binding() -> None:
    """Wrap the canonical adapter once so issued packets enter the bounded registry."""

    from aura_construction_adapter import ConstructionArenaAdapter

    current = ConstructionArenaAdapter.build_runtime_packet
    if getattr(current, "__aura_runtime_binding__", False):
        return

    @wraps(current)
    def bound_build_runtime_packet(self: Any, *args: Any, **kwargs: Any) -> dict[str, Any]:
        packet = current(self, *args, **kwargs)
        register_construction_runtime_packet(packet, state_digest=str(packet.get("state_digest") or ""))
        return packet

    setattr(bound_build_runtime_packet, "__aura_runtime_binding__", True)
    ConstructionArenaAdapter.build_runtime_packet = bound_build_runtime_packet


install_construction_runtime_binding()


__all__ = [
    "CONSTRUCTION_RUNTIME_BINDING_VERSION",
    "MAX_CANONICAL_CONSTRUCTION_RUNTIME_PACKETS",
    "install_construction_runtime_binding",
    "register_construction_runtime_packet",
    "require_canonical_construction_runtime_packet",
]
