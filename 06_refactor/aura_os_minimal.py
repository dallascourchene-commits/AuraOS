"""AuraOS Stage 06 minimal refactor substrate.

Four primitives only:
- P_INGRESS: anchored causal-cone admission.
- P_ROUTER: conservative six-slot route compilation.
- P_FENCE: fail-closed consequence / proof / authority preflight.
- P_RESIDUAL: generation-coherent verified-PASS subtraction.

Claim ceiling: Stage 06 candidate. No persistence, model egress, cryptography,
policy minting, deployment, or canonical authority. Python 3.10+ stdlib only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
import math
from typing import Any, Callable, Mapping, Sequence

ORIGIN = (0, 0, 0, 0)
SLOT_ORDER = ("DIR", "ASP", "CLASS", "SUBJ", "VOICE", "STEM")
REQUIRED_PROOF_CHECKS = (
    "authorized_root_binding",
    "generation_coherence",
    "merkle_inclusion",
    "zk_public_input_binding",
    "zk_verification",
    "freshness",
)
# Kernel-owned terminal selection. Unknown classes fail closed.
_STEM_BY_CLASS = {
    "READ": "INSPECT",
    "VERIFY": "VERIFY",
    "CHANGE": "PROPOSE",
    "WRITE": "PROPOSE",
    "REPAIR": "REPAIR",
}
# The module retains no task payload, transcript, receipt cache, or mutable registry.
IDLE_STATE: tuple[()] = ()


class Disposition(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


class EffectDecision(str, Enum):
    ADMIT = "ADMIT"
    BLOCK = "BLOCK"


@dataclass(frozen=True, slots=True)
class IngressPacket:
    causal_cone: frozenset[str]
    origin: tuple[int, int, int, int] = field(default=ORIGIN, init=False)


@dataclass(frozen=True, slots=True)
class TriProposalBundle:
    g_r: Mapping[str, object]
    g_f: Mapping[str, object]
    g_c: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class CausalFence:
    r_d: float | None
    c_d: float | None
    fail_closed_flag: bool = True


@dataclass(frozen=True, slots=True)
class PassReceipt:
    receipt_id: str
    obligation_id: str
    disposition: Disposition
    generation: str | None
    verified: bool
    current: bool | None = True


@dataclass(slots=True)
class ResidualBuffer:
    obligations: set[str] = field(default_factory=set)
    pass_receipts: set[str] = field(default_factory=set)


@dataclass(frozen=True, slots=True)
class ObligationResult:
    disposition: Disposition
    reason: str = ""


Evaluator = Callable[[Mapping[str, Any]], ObligationResult]


@dataclass(frozen=True, slots=True)
class RequiredObligation:
    obligation_id: str
    evaluator: Evaluator = field(compare=False, repr=False)
    cost_tier: int = 2
    estimated_cost: float = 1.0
    estimated_fail_probability: float = 0.0


@dataclass(frozen=True, slots=True)
class ContainmentResult:
    disposition: Disposition
    evaluated: tuple[str, ...]
    first_fail: str | None = None
    first_unknown: str | None = None
    reason: str = ""


@dataclass(frozen=True, slots=True)
class RouteDecision:
    decision: EffectDecision
    slots: tuple[tuple[str, str], ...] = ()
    route_id: str = ""
    reason: str = ""

    @property
    def valid(self) -> bool:
        return self.decision is EffectDecision.ADMIT and tuple(k for k, _ in self.slots) == SLOT_ORDER


@dataclass(frozen=True, slots=True)
class VerificationEvidence:
    required_generation: str
    checks: Mapping[str, bool | None]


@dataclass(frozen=True, slots=True)
class PreflightResult:
    decision: EffectDecision
    reason: str


@dataclass(frozen=True, slots=True)
class ResidualResult:
    disposition: Disposition
    residual: frozenset[str]
    discharged: frozenset[str]
    accepted_receipts: frozenset[str]
    rejected_receipts: tuple[tuple[str, str], ...]


def _text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def p_ingress(causal_cone: Sequence[str] | set[str] | frozenset[str]) -> IngressPacket:
    """Admit only explicit non-empty node identifiers; origin is non-overridable."""
    try:
        nodes = tuple(causal_cone)
    except TypeError as exc:
        raise ValueError("causal_cone must be an iterable of node identifiers") from exc
    clean: set[str] = set()
    for node in nodes:
        item = _text(node)
        if item is None:
            raise ValueError("causal_cone contains an invalid node identifier")
        clean.add(item)
    if not clean:
        raise ValueError("causal_cone must not be empty")
    return IngressPacket(frozenset(clean))


def order_for_falsification(checks: Sequence[RequiredObligation]) -> tuple[RequiredObligation, ...]:
    """Cheap / high expected-defeat checks first; stable by obligation id."""
    def key(item: RequiredObligation) -> tuple[int, float, str]:
        cost = max(float(item.estimated_cost), 1e-12)
        return (item.cost_tier, -(float(item.estimated_fail_probability) / cost), item.obligation_id)
    return tuple(sorted(checks, key=key))


def evaluate_containment(
    facts: Mapping[str, Any], required: Sequence[RequiredObligation]
) -> ContainmentResult:
    """Definite FAIL short-circuits; UNKNOWN survives unless a later FAIL dominates."""
    evaluated: list[str] = []
    first_unknown: str | None = None
    first_unknown_reason = ""
    for check in order_for_falsification(required):
        result = check.evaluator(facts)
        evaluated.append(check.obligation_id)
        if result.disposition is Disposition.FAIL:
            return ContainmentResult(
                Disposition.FAIL,
                tuple(evaluated),
                first_fail=check.obligation_id,
                first_unknown=first_unknown,
                reason=result.reason,
            )
        if result.disposition is Disposition.UNKNOWN and first_unknown is None:
            first_unknown = check.obligation_id
            first_unknown_reason = result.reason
    if first_unknown is not None:
        return ContainmentResult(
            Disposition.UNKNOWN,
            tuple(evaluated),
            first_unknown=first_unknown,
            reason=first_unknown_reason,
        )
    return ContainmentResult(Disposition.PASS, tuple(evaluated))


def _proposal_effect_class(proposals: TriProposalBundle) -> str | None:
    """Conservative adjudication: all three proposal surfaces must agree."""
    maps = (proposals.g_r, proposals.g_f, proposals.g_c)
    if any(not isinstance(m, Mapping) or not m for m in maps):
        return None
    values = [_text(m.get("effect_class")) for m in maps]
    if any(v is None for v in values) or len(set(values)) != 1:
        return None
    return values[0].upper()  # type: ignore[union-attr]


def p_router(
    packet: IngressPacket,
    proposals: TriProposalBundle,
    residual: ResidualBuffer,
    *,
    direction: str | None,
    phase: str | None,
    subject: str | None,
    authority_voice: str | None,
    authority_current: bool | None,
) -> RouteDecision:
    """Compile a six-slot route without fabricating phase, authority, or target."""
    if packet.origin != ORIGIN:
        return RouteDecision(EffectDecision.BLOCK, reason="ORIGIN_MISMATCH")
    d = _text(direction)
    if d is None or d not in packet.causal_cone:
        return RouteDecision(EffectDecision.BLOCK, reason="DIR_OUTSIDE_CAUSAL_CONE")
    effect_class = _proposal_effect_class(proposals)
    if effect_class is None:
        return RouteDecision(EffectDecision.BLOCK, reason="TRI_PROPOSAL_INCOMPLETE_OR_DIVERGENT")
    asp = _text(phase)
    if asp is None:
        return RouteDecision(EffectDecision.BLOCK, reason="ASP_UNRESOLVED")
    subj = _text(subject)
    if subj is None or subj not in residual.obligations or subj not in packet.causal_cone:
        return RouteDecision(EffectDecision.BLOCK, reason="SUBJ_NOT_LIVE_IN_CONE")
    voice = _text(authority_voice)
    if voice is None or authority_current is not True:
        return RouteDecision(EffectDecision.BLOCK, reason="VOICE_AUTHORITY_UNRESOLVED")
    stem = _STEM_BY_CLASS.get(effect_class)
    if stem is None:
        return RouteDecision(EffectDecision.BLOCK, reason="STEM_UNRESOLVED_FOR_CLASS")
    slots = (
        ("DIR", d),
        ("ASP", asp),
        ("CLASS", effect_class),
        ("SUBJ", subj),
        ("VOICE", voice),
        ("STEM", stem),
    )
    route_id = _canonical_sha256({"slots": slots})
    return RouteDecision(EffectDecision.ADMIT, slots=slots, route_id=route_id, reason="FST_VALID_ROUTE")


def _causal_fence_passes(fence: CausalFence) -> tuple[bool, str]:
    if fence.fail_closed_flag is not True:
        return False, "FAIL_CLOSED_DISABLED"
    if isinstance(fence.r_d, bool) or isinstance(fence.c_d, bool):
        return False, "CAUSAL_TIMING_UNKNOWN"
    if not isinstance(fence.r_d, (int, float)) or not isinstance(fence.c_d, (int, float)):
        return False, "CAUSAL_TIMING_UNKNOWN"
    r_d, c_d = float(fence.r_d), float(fence.c_d)
    if not math.isfinite(r_d) or not math.isfinite(c_d):
        return False, "CAUSAL_TIMING_UNKNOWN"
    if not r_d < c_d:
        return False, "CAUSAL_FENCE_VIOLATION"
    return True, "CAUSAL_FENCE_PASS"


def p_fence(
    route: RouteDecision,
    fence: CausalFence,
    verification: VerificationEvidence,
    *,
    authority_current: bool | None,
) -> PreflightResult:
    """Effect is admitted only after route, causal, proof, generation and authority gates."""
    if not route.valid:
        return PreflightResult(EffectDecision.BLOCK, "NO_VALID_ROUTE")
    causal_ok, reason = _causal_fence_passes(fence)
    if not causal_ok:
        return PreflightResult(EffectDecision.BLOCK, reason)
    if _text(verification.required_generation) is None:
        return PreflightResult(EffectDecision.BLOCK, "GENERATION_UNKNOWN")
    for name in REQUIRED_PROOF_CHECKS:
        value = verification.checks.get(name)
        if value is not True:
            suffix = "UNKNOWN" if value is None else "FAIL"
            return PreflightResult(EffectDecision.BLOCK, f"{name.upper()}_{suffix}")
    if authority_current is not True:
        return PreflightResult(EffectDecision.BLOCK, "EFFECT_AUTHORITY_UNKNOWN_OR_DENIED")
    return PreflightResult(EffectDecision.ADMIT, "EFFECT_ADMITTED")


def p_residual(
    buffer: ResidualBuffer,
    receipts: Sequence[PassReceipt],
    *,
    required_generation: str,
) -> ResidualResult:
    """R_t = O \\ D_t, where D_t contains only current verified coherent PASS receipts."""
    gen = _text(required_generation)
    if gen is None:
        return ResidualResult(
            Disposition.UNKNOWN,
            frozenset(buffer.obligations),
            frozenset(),
            frozenset(),
            (("<generation>", "REQUIRED_GENERATION_UNKNOWN"),),
        )

    obligations = set(buffer.obligations)
    discharged: set[str] = set()
    accepted: set[str] = set()
    rejected: list[tuple[str, str]] = []
    saw_unknown = False
    saw_fail = False

    for receipt in receipts:
        rid = _text(receipt.receipt_id) or "<invalid-receipt>"
        obligation = _text(receipt.obligation_id)
        if obligation is None or obligation not in obligations:
            rejected.append((rid, "NOT_A_REQUIRED_OBLIGATION"))
            continue
        if receipt.disposition is Disposition.FAIL:
            rejected.append((rid, "DEFINITE_FAIL"))
            saw_fail = True
            continue
        if receipt.disposition is Disposition.UNKNOWN:
            rejected.append((rid, "UNKNOWN_RECEIPT"))
            saw_unknown = True
            continue
        if receipt.verified is not True:
            rejected.append((rid, "UNVERIFIED_PASS"))
            saw_unknown = True
            continue
        if receipt.generation is None:
            rejected.append((rid, "MISSING_GENERATION"))
            saw_unknown = True
            continue
        if receipt.generation != gen:
            rejected.append((rid, "GENERATION_MISMATCH"))
            saw_fail = True
            continue
        if receipt.current is not True:
            rejected.append((rid, "STALE_OR_UNKNOWN_CURRENTNESS"))
            saw_unknown = True
            continue
        discharged.add(obligation)
        accepted.add(rid)

    residual = obligations - discharged
    buffer.obligations = residual
    buffer.pass_receipts = accepted
    if saw_fail:
        disposition = Disposition.FAIL
    elif residual or saw_unknown:
        disposition = Disposition.UNKNOWN
    else:
        disposition = Disposition.PASS
    return ResidualResult(
        disposition,
        frozenset(residual),
        frozenset(discharged),
        frozenset(accepted),
        tuple(rejected),
    )


def idle_state() -> tuple[()]:
    """No task state is retained by the substrate while idle."""
    return IDLE_STATE


__all__ = [
    "CausalFence", "ContainmentResult", "Disposition", "EffectDecision",
    "IngressPacket", "ObligationResult", "PassReceipt", "PreflightResult",
    "REQUIRED_PROOF_CHECKS", "RequiredObligation", "ResidualBuffer",
    "ResidualResult", "RouteDecision", "SLOT_ORDER", "TriProposalBundle",
    "VerificationEvidence", "evaluate_containment", "idle_state",
    "order_for_falsification", "p_fence", "p_ingress", "p_residual", "p_router",
]
