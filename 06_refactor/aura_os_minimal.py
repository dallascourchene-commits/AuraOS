#!/usr/bin/env python3
"""AuraOS minimal four-primitive Stage 06 candidate.

Scope:
- P_INGRESS: validate fixed origin and admitted causal cone.
- P_ROUTER: compile a deterministic six-slot route without third-party libraries.
- P_FENCE: fail closed unless causal timing evidence is independently verified.
- P_RESIDUAL: subtract only verified, generation-coherent PASS receipts.

Claim ceiling:
This is a Stage 06 candidate. It does not mint authority, implement cryptography,
prove provider independence, persist canonical state, or replace source owners.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, TypeAlias


Origin4D: TypeAlias = tuple[int, int, int, int]
CausalCone: TypeAlias = frozenset[str]
ProposalPayload: TypeAlias = Mapping[str, object]
SlotTuple: TypeAlias = tuple[tuple[str, str], ...]


class Disposition(str, Enum):
    PASS = "PASS"
    FAIL_CLOSED = "FAIL_CLOSED"
    UNKNOWN = "UNKNOWN"
    BLOCK = "BLOCK"


@dataclass(frozen=True, slots=True)
class Check:
    disposition: Disposition
    reason: str

    @property
    def passed(self) -> bool:
        return self.disposition is Disposition.PASS


@dataclass(frozen=True, slots=True)
class IngressPacket:
    causal_cone: CausalCone = field(default_factory=frozenset)
    origin: Origin4D = field(default=(0, 0, 0, 0), init=False)


@dataclass(frozen=True, slots=True)
class TriProposalBundle:
    g_r: ProposalPayload
    g_f: ProposalPayload
    g_c: ProposalPayload


@dataclass(frozen=True, slots=True)
class CausalFence:
    r_d: float
    c_d: float
    fail_closed_flag: bool = True


@dataclass(slots=True)
class ResidualBuffer:
    obligations: set[str] = field(default_factory=set)
    pass_receipts: set[str] = field(default_factory=set)


@dataclass(frozen=True, slots=True)
class PassReceipt:
    receipt_id: str
    obligation_id: str
    generation: str
    verified: bool


@dataclass(frozen=True, slots=True)
class RouteResult:
    check: Check
    slots: SlotTuple = ()


@dataclass(frozen=True, slots=True)
class ResidualResult:
    check: Check
    residual_obligations: frozenset[str]
    discharged_obligations: frozenset[str]


def p_ingress(packet: IngressPacket) -> Check:
    """Admit only the fixed Aura origin with a nonempty bounded causal cone."""
    if packet.origin != (0, 0, 0, 0):
        return Check(Disposition.FAIL_CLOSED, "origin_mismatch")
    if not packet.causal_cone:
        return Check(Disposition.UNKNOWN, "causal_cone_unresolved")
    if any(not str(node).strip() for node in packet.causal_cone):
        return Check(Disposition.FAIL_CLOSED, "malformed_causal_cone_node")
    return Check(Disposition.PASS, "ingress_admitted")


def _proposal_surfaces_complete(bundle: TriProposalBundle) -> Check:
    if not bundle.g_r or not bundle.g_f or not bundle.g_c:
        return Check(Disposition.UNKNOWN, "tri_proposal_surface_missing")
    return Check(Disposition.PASS, "tri_proposal_surfaces_preserved")


def p_router(
    packet: IngressPacket,
    bundle: TriProposalBundle,
    residual: ResidualBuffer,
    *,
    runtime_phase: str | None,
    authority_voice: str | None,
    authority_verified: bool,
    admitted_class: str | None,
    stem: str | None,
    joint_dependency_complete: bool | None,
    independent_defeat_path: bool | None,
) -> RouteResult:
    """Compile an exact six-slot route after required external facts are supplied.

    No weighting, provider call, VSA, numpy, or hidden authority plane is used.
    The function refuses to choose an exact target when more than one live
    in-cone obligation remains.
    """
    ingress = p_ingress(packet)
    if not ingress.passed:
        return RouteResult(ingress)

    proposals = _proposal_surfaces_complete(bundle)
    if not proposals.passed:
        return RouteResult(proposals)

    if joint_dependency_complete is not True:
        disposition = Disposition.UNKNOWN if joint_dependency_complete is None else Disposition.FAIL_CLOSED
        return RouteResult(Check(disposition, "joint_dependency_not_proven_complete"))

    if independent_defeat_path is not True:
        disposition = Disposition.UNKNOWN if independent_defeat_path is None else Disposition.FAIL_CLOSED
        return RouteResult(Check(disposition, "independent_falsifier_not_established"))

    if not runtime_phase:
        return RouteResult(Check(Disposition.UNKNOWN, "runtime_phase_unresolved"))

    if not authority_voice:
        return RouteResult(Check(Disposition.UNKNOWN, "authority_voice_unresolved"))

    if not authority_verified:
        return RouteResult(Check(Disposition.BLOCK, "authority_not_independently_verified"))

    if not admitted_class:
        return RouteResult(Check(Disposition.UNKNOWN, "admitted_class_unresolved"))

    if not stem:
        return RouteResult(Check(Disposition.UNKNOWN, "terminal_stem_unresolved"))

    live_targets = sorted(residual.obligations.intersection(packet.causal_cone))
    if not live_targets:
        return RouteResult(Check(Disposition.UNKNOWN, "no_live_in_cone_obligation"))
    if len(live_targets) != 1:
        return RouteResult(Check(Disposition.UNKNOWN, "exact_subject_not_uniquely_resolved"))

    subject = live_targets[0]
    slots: SlotTuple = (
        ("DIR", f"CONE:{subject}"),
        ("ASP", str(runtime_phase)),
        ("CLASS", str(admitted_class)),
        ("SUBJ", subject),
        ("VOICE", str(authority_voice)),
        ("STEM", str(stem)),
    )
    return RouteResult(Check(Disposition.PASS, "six_slot_route_compiled"), slots)


def p_fence(fence: CausalFence, *, timing_evidence_verified: bool) -> Check:
    """PASS only on independently verified R_d < C_d with fail-closed enabled."""
    if not fence.fail_closed_flag:
        return Check(Disposition.FAIL_CLOSED, "fail_closed_flag_disabled")
    if not timing_evidence_verified:
        return Check(Disposition.UNKNOWN, "causal_timing_evidence_unverified")
    if not (fence.r_d < fence.c_d):
        return Check(Disposition.FAIL_CLOSED, "recovery_deadline_not_before_consequence")
    return Check(Disposition.PASS, "causal_fence_satisfied")


def p_residual(
    buffer: ResidualBuffer,
    receipt_index: Mapping[str, PassReceipt],
    *,
    required_generation: str | None,
) -> ResidualResult:
    """Compute O \\ D using only verified PASS receipts for one exact generation."""
    if not required_generation:
        return ResidualResult(
            Check(Disposition.UNKNOWN, "required_generation_unresolved"),
            frozenset(buffer.obligations),
            frozenset(),
        )

    residual = set(buffer.obligations)
    discharged: set[str] = set()
    saw_unknown = False
    saw_stale = False

    for receipt_id in sorted(buffer.pass_receipts):
        receipt = receipt_index.get(receipt_id)
        if receipt is None:
            saw_unknown = True
            continue
        if not receipt.verified:
            saw_unknown = True
            continue
        if receipt.generation != required_generation:
            saw_stale = True
            continue
        if receipt.obligation_id in residual:
            residual.remove(receipt.obligation_id)
            discharged.add(receipt.obligation_id)

    if saw_stale:
        check = Check(Disposition.BLOCK, "stale_generation_receipt_rejected")
    elif saw_unknown:
        check = Check(Disposition.UNKNOWN, "receipt_missing_or_unverified")
    else:
        check = Check(Disposition.PASS, "residual_pruned_from_verified_current_receipts")

    return ResidualResult(check, frozenset(residual), frozenset(discharged))


__all__ = [
    "CausalFence",
    "Check",
    "Disposition",
    "IngressPacket",
    "PassReceipt",
    "ResidualBuffer",
    "ResidualResult",
    "RouteResult",
    "TriProposalBundle",
    "p_fence",
    "p_ingress",
    "p_residual",
    "p_router",
]
