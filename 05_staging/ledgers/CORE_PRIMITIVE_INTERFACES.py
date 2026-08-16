"""AuraOS core primitive interface contracts for the W2 -> W3 handoff.

Hydration boundary: L1 -> L2.
Dependency policy: Python standard library only.

This module intentionally defines structure only. It does not perform routing,
hydration, adjudication, persistence, or framework-specific validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, TypeAlias


Origin4D: TypeAlias = tuple[int, int, int, int]
CausalCone: TypeAlias = frozenset[str]
ProposalPayload: TypeAlias = Mapping[str, object]


@dataclass(frozen=True, slots=True)
class IngressPacket:
    """Minimal ingress contract anchored at the Aura origin.

    ``causal_cone`` carries the node identifiers belonging to W(delta).
    The origin is fixed by contract and is not caller-overridable.
    """

    causal_cone: CausalCone = field(default_factory=frozenset)
    origin: Origin4D = field(default=(0, 0, 0, 0), init=False)


@dataclass(frozen=True, slots=True)
class TriProposalBundle:
    """Competing proposal surfaces for minimal delta, falsification, and risk."""

    g_r: ProposalPayload
    g_f: ProposalPayload
    g_c: ProposalPayload


@dataclass(frozen=True, slots=True)
class CausalFence:
    """Causal recovery/consequence boundary supplied to fail-closed checks."""

    r_d: float
    c_d: float
    fail_closed_flag: bool = True


@dataclass(slots=True)
class ResidualBuffer:
    """Mutable task-local residual state; no authority is implied by membership."""

    obligations: set[str] = field(default_factory=set)
    pass_receipts: set[str] = field(default_factory=set)


__all__ = [
    "CausalFence",
    "IngressPacket",
    "ResidualBuffer",
    "TriProposalBundle",
]
