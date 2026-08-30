"""AWJ-031-E bounded C369 / route-shell / lifecycle reference.

This module is a staged executable contract derived from the Drive-owned Aura Cell
Kernel V0.3 / AWJ-031-E synthetic reference. It is not a canonical runtime owner,
performance claim, novelty claim, or authority source.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
import json
from typing import Iterable, Mapping, Sequence

SOURCE_DRIVE_ID = "1XUYE51d5j5QbYCCl865eP-gHZyaeiVtm"
SOURCE_SHA256 = "df9f11d562685ad7213a1beab8c07b6aba9c5cad1417ed0c8e0418a92876f051"
AXES = ("X", "Y", "Z")
Direction = tuple[int, int, int]


def _direction(d: Direction) -> Direction:
    if not isinstance(d, tuple) or len(d) != 3:
        raise ValueError("direction must be a 3-tuple")
    if any(isinstance(v, bool) or not isinstance(v, int) or v not in (-1, 0, 1) for v in d):
        raise ValueError("direction components must be -1, 0, +1 integers")
    return d


def encode_n(d: Direction) -> int:
    dx, dy, dz = _direction(d)
    return (dx + 1) + 3 * (dy + 1) + 9 * (dz + 1)


def decode_n(n: int) -> Direction:
    if isinstance(n, bool) or not isinstance(n, int) or not 0 <= n <= 26:
        raise ValueError("N must be an integer in [0,26]")
    q = n
    digits: list[int] = []
    for _ in range(3):
        digits.append((q % 3) - 1)
        q //= 3
    return tuple(digits)  # type: ignore[return-value]


def active_axes(d: Direction) -> int:
    return sum(v != 0 for v in _direction(d))


def route_shell(d: Direction) -> int:
    return 3 * active_axes(d)


def lambda_factor(d: Direction, m: int) -> Fraction:
    if isinstance(m, bool) or not isinstance(m, int) or m < 0:
        raise ValueError("m must be a non-negative integer")
    return Fraction(1, 2 ** (m * active_axes(d)))


def refine_then_step(
    u: Direction,
    e: Direction,
    d: Direction,
    m: int,
) -> tuple[Direction, Direction]:
    if isinstance(m, bool) or not isinstance(m, int) or m < 0:
        raise ValueError("m must be a non-negative integer")
    _direction(d)
    if len(u) != 3 or len(e) != 3 or any(isinstance(v, bool) or not isinstance(v, int) for v in (*u, *e)):
        raise ValueError("u/e must be integer 3-tuples")
    u2: list[int] = []
    e2: list[int] = []
    for ui, ei, di in zip(u, e, d):
        ell = m if di != 0 else 0
        e2.append(ei + ell)
        u2.append((2**ell) * ui + di)
    return tuple(u2), tuple(e2)  # type: ignore[return-value]


def exact_position(u: Sequence[int], e: Sequence[int]) -> tuple[Fraction, ...]:
    if len(u) != len(e):
        raise ValueError("u/e length mismatch")
    if any(isinstance(v, bool) or not isinstance(v, int) for v in (*u, *e)):
        raise ValueError("u/e must contain integers")
    if any(exp < 0 for exp in e):
        raise ValueError("negative dyadic exponent")
    return tuple(Fraction(ui, 2**ei) for ui, ei in zip(u, e))


@dataclass(frozen=True)
class LawfulTransitionReceiptV1:
    receipt_id: str
    source_current: bool
    source_bound: bool
    dependency_closed: bool
    within_authority: bool
    negative_space_clear: bool
    review_boundary_preserved: bool
    human_gate_not_bypassed: bool
    source_generation: int

    @property
    def lawful(self) -> bool:
        return bool(self.receipt_id) and all(
            (
                self.source_current,
                self.source_bound,
                self.dependency_closed,
                self.within_authority,
                self.negative_space_clear,
                self.review_boundary_preserved,
                self.human_gate_not_bypassed,
            )
        )


@dataclass(frozen=True)
class AxisClosureReceiptV1:
    receipt_id: str
    axis: str
    generation: int
    source_digest: str
    current: bool
    matched: bool
    lawful_transition_ref: str


@dataclass(frozen=True)
class C369BridgeReceiptV1:
    bridge_receipt_id: str
    axis_receipts: tuple[AxisClosureReceiptV1, ...]
    skipped_seams: tuple[str, ...]
    skipped_seams_reconstructible: bool
    gate_bypass: bool
    revoked: bool
    before_generation: int
    after_generation: int
    before_coordinate: tuple[int, int]
    after_coordinate: tuple[int, int]


@dataclass(frozen=True)
class Orientation369ReceiptV1:
    derivation_receipt_27: str
    derivation_receipt_369: str
    transition_receipt: str
    source_generation: int
    current_n: int
    current_s: int
    permitted_moves: tuple[int, ...]


@dataclass(frozen=True)
class ReductionReceiptV1:
    reduction_id: str
    objective: str
    child_refs: tuple[str, ...]
    summary_digest: str


@dataclass(frozen=True)
class MovementReceiptV1:
    movement_id: str
    direction: Direction
    n: int
    s: int
    m: int
    before_position: tuple[str, str, str]
    after_position: tuple[str, str, str]


@dataclass(frozen=True)
class CreationLifecycleReceiptV1:
    lifecycle_id: str
    start_generation: int
    end_generation: int
    start_stage: int
    end_stage: int
    authority_before: int
    authority_after: int
    source_current: bool
    human_gate_satisfied: bool


def make_lawful(receipt_id: str, generation: int, **overrides: bool) -> LawfulTransitionReceiptV1:
    values = {
        "source_current": True,
        "source_bound": True,
        "dependency_closed": True,
        "within_authority": True,
        "negative_space_clear": True,
        "review_boundary_preserved": True,
        "human_gate_not_bypassed": True,
    }
    unknown = set(overrides) - set(values)
    if unknown:
        raise ValueError(f"unknown lawful override(s): {sorted(unknown)}")
    values.update(overrides)
    return LawfulTransitionReceiptV1(receipt_id, source_generation=generation, **values)


def validate_orientation(r: Orientation369ReceiptV1) -> bool:
    try:
        d = decode_n(r.current_n)
    except ValueError:
        return False
    return (
        bool(r.derivation_receipt_27)
        and bool(r.derivation_receipt_369)
        and bool(r.transition_receipt)
        and isinstance(r.source_generation, int)
        and not isinstance(r.source_generation, bool)
        and r.source_generation >= 0
        and r.current_s in (0, 3, 6, 9)
        and r.current_s == route_shell(d)
        and bool(r.permitted_moves)
        and all(move in (0, 3, 6, 9) for move in r.permitted_moves)
    )


def validate_c369(
    bridge: C369BridgeReceiptV1,
    lawful_receipts: Mapping[str, LawfulTransitionReceiptV1],
) -> tuple[bool, str]:
    if bridge.gate_bypass:
        return False, "GATE_BYPASS"
    if bridge.revoked:
        return False, "REVOKED"
    if not bridge.bridge_receipt_id:
        return False, "MISSING_BRIDGE_RECEIPT"
    if not bridge.skipped_seams_reconstructible:
        return False, "UNRECONSTRUCTIBLE_SKIPPED_SEAM"
    if len(bridge.axis_receipts) != 3:
        return False, "AXIS_RECEIPT_CARDINALITY"
    if {r.axis for r in bridge.axis_receipts} != set(AXES):
        return False, "MISSING_OR_DUPLICATE_AXIS"
    generations = {r.generation for r in bridge.axis_receipts}
    if len(generations) != 1 or bridge.before_generation not in generations:
        return False, "GENERATION_MISMATCH"
    if len({r.source_digest for r in bridge.axis_receipts}) != 1:
        return False, "SOURCE_MISMATCH"
    if any(not r.current for r in bridge.axis_receipts):
        return False, "STALE_AXIS_RECEIPT"
    if any(not r.matched for r in bridge.axis_receipts):
        return False, "MISMATCHED_AXIS_RECEIPT"
    if any(not r.receipt_id or not r.source_digest or not r.lawful_transition_ref for r in bridge.axis_receipts):
        return False, "INCOMPLETE_AXIS_RECEIPT"
    for axis_r in bridge.axis_receipts:
        lawful = lawful_receipts.get(axis_r.lawful_transition_ref)
        if lawful is None:
            return False, "MISSING_LAWFUL_TRANSITION"
        if not lawful.lawful:
            return False, "UNLAWFUL_AXIS_TRANSITION"
        if lawful.source_generation != axis_r.generation:
            return False, "LAWFUL_RECEIPT_GENERATION_MISMATCH"
    if bridge.after_coordinate != (
        bridge.before_coordinate[0] + 2,
        bridge.before_coordinate[1] + 2,
    ):
        return False, "BAD_COUPLED_LIFT"
    if bridge.after_generation != bridge.before_generation:
        return False, "C369_CANNOT_INFER_LIFECYCLE_GENERATION"
    return True, "PASS"


def stage10_rebase(
    generation: int,
    authority_before: int,
    authority_after: int,
    source_current: bool,
    human_gate_satisfied: bool,
) -> CreationLifecycleReceiptV1:
    if any(isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in (generation, authority_before, authority_after)):
        raise ValueError("generation/authority must be non-negative integers")
    if authority_after > authority_before:
        raise ValueError("lifecycle rebase cannot self-authorize")
    if not source_current or not human_gate_satisfied:
        raise ValueError("lifecycle rebase requires current source and human gate")
    return CreationLifecycleReceiptV1(
        lifecycle_id=f"LIFE-{generation}-{generation + 1}",
        start_generation=generation,
        end_generation=generation + 1,
        start_stage=10,
        end_stage=1,
        authority_before=authority_before,
        authority_after=authority_after,
        source_current=source_current,
        human_gate_satisfied=human_gate_satisfied,
    )


def affected_cone(changed: Iterable[str], dependencies: Mapping[str, set[str]]) -> set[str]:
    out = set(changed)
    frontier = list(out)
    while frontier:
        node = frontier.pop()
        for child in dependencies.get(node, set()):
            if child not in out:
                out.add(child)
                frontier.append(child)
    return out


def seam_digest(seams: Sequence[str]) -> str:
    if any(not isinstance(v, str) or not v for v in seams):
        raise ValueError("seams must be non-empty strings")
    payload = json.dumps(list(seams), ensure_ascii=False, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()
