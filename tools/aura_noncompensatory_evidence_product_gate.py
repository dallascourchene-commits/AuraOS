#!/usr/bin/env python3
"""Non-compensatory product gate for AuraOS evidence and hard constraints.

Positive evidence is valuable only inside the feasible region defined by independent
hard gates. Evidence magnitude cannot pay, average away, or compensate for a failed
orthogonal gate.

This generic D0 membrane is derived from two exact-green other-agent consequences:
- PR671: bounded official GLM equal-rate canary evidence is favorable inside its
  representative scientific scope.
- PR672: the source-bound C2 request remains HOLD because official index/header
  admission is independently incomplete.

PR674 owns the GLM-specific result->C2 composition. This module owns only the
reusable generic product-gate law.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Sequence

VERSION = "AURA_NONCOMPENSATORY_EVIDENCE_PRODUCT_GATE_V1"
PR671_HEAD = "23c8345a1e3d5034ce88bea1ab32c69c1a9cf3f2"
PR671_RUN = 33400399223
PR672_HEAD = "7340091202f3f1a859841c3ec4314191f18fa1ad"
PR672_RUN = 33400557094

SUPPORTS = "SUPPORTS"
NEUTRAL = "NEUTRAL"
OPPOSES = "OPPOSES"
VALID_OUTCOMES = {SUPPORTS, NEUTRAL, OPPOSES}

HOLD_HARD_GATE = "HOLD_HARD_GATE"
ELIGIBLE_BOUNDED_PROPOSAL = "ELIGIBLE_BOUNDED_PROPOSAL"
STOP_NO_POSITIVE_EVIDENCE = "STOP_NO_POSITIVE_EVIDENCE"
STOP_OPPOSING_EVIDENCE = "STOP_OPPOSING_EVIDENCE"


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class EvidenceSignal:
    signal_id: str
    outcome: str
    strength: int
    scope: str
    evidence_digest: str

    def validate(self) -> None:
        if not self.signal_id.strip():
            raise ValueError("SIGNAL_ID_REQUIRED")
        if self.outcome not in VALID_OUTCOMES:
            raise ValueError("UNKNOWN_EVIDENCE_OUTCOME")
        if type(self.strength) is not int or self.strength < 0:
            raise ValueError("EVIDENCE_STRENGTH_MUST_BE_NONNEGATIVE_INT")
        if not self.scope.strip():
            raise ValueError("EVIDENCE_SCOPE_REQUIRED")
        if len(self.evidence_digest) != 64 or any(c not in "0123456789abcdef" for c in self.evidence_digest):
            raise ValueError("INVALID_EVIDENCE_DIGEST")


@dataclass(frozen=True)
class HardGate:
    gate_id: str
    passed: bool
    domain: str
    blocker: str | None = None

    def validate(self) -> None:
        if not self.gate_id.strip():
            raise ValueError("GATE_ID_REQUIRED")
        if type(self.passed) is not bool:
            raise ValueError("GATE_PASSED_MUST_BE_BOOL")
        if not self.domain.strip():
            raise ValueError("GATE_DOMAIN_REQUIRED")
        if self.passed and self.blocker is not None:
            raise ValueError("PASSED_GATE_CANNOT_HAVE_BLOCKER")
        if not self.passed and (self.blocker is None or not self.blocker.strip()):
            raise ValueError("FAILED_GATE_REQUIRES_BLOCKER")


@dataclass(frozen=True)
class ProductGateReceipt:
    schema: str
    parent_heads: tuple[str, str]
    parent_runs: tuple[int, int]
    signal_count: int
    gate_count: int
    all_hard_gates_pass: bool
    failed_gate_ids: tuple[str, ...]
    blocker_set: tuple[str, ...]
    evidence_policy_evaluated: bool
    positive_evidence_present: bool
    opposing_evidence_present: bool
    max_support_strength: int
    disposition: str
    bounded_proposal_eligible: bool
    evidence_can_compensate_for_failed_gate: bool
    evidence_magnitude_changes_feasibility: bool
    k27_coordinate_grants_constraint_satisfaction: bool
    semantic_truth_minted: bool
    effect_authority_granted: bool
    native_private_transformer_kv_accessed: bool
    gate10_promoted: bool
    merge_or_deployment_authorized: bool

    @property
    def receipt_digest(self) -> str:
        return _sha(asdict(self))


def evaluate_product_gate(
    *, signals: Sequence[EvidenceSignal], gates: Sequence[HardGate]
) -> ProductGateReceipt:
    if not signals:
        raise ValueError("AT_LEAST_ONE_EVIDENCE_SIGNAL_REQUIRED")
    if not gates:
        raise ValueError("AT_LEAST_ONE_HARD_GATE_REQUIRED")
    for signal in signals:
        signal.validate()
    for gate in gates:
        gate.validate()

    signal_ids = [s.signal_id for s in signals]
    gate_ids = [g.gate_id for g in gates]
    if len(signal_ids) != len(set(signal_ids)):
        raise ValueError("DUPLICATE_SIGNAL_ID")
    if len(gate_ids) != len(set(gate_ids)):
        raise ValueError("DUPLICATE_GATE_ID")

    failed = tuple(sorted(g.gate_id for g in gates if not g.passed))
    blockers = tuple(sorted(g.blocker for g in gates if not g.passed and g.blocker is not None))
    feasible = not failed
    positive = any(s.outcome == SUPPORTS for s in signals)
    opposing = any(s.outcome == OPPOSES for s in signals)
    max_support = max((s.strength for s in signals if s.outcome == SUPPORTS), default=0)

    # Hard gates are evaluated first and are non-compensatory by construction.
    if not feasible:
        evaluated = False
        disposition = HOLD_HARD_GATE
        eligible = False
    else:
        evaluated = True
        if opposing:
            disposition = STOP_OPPOSING_EVIDENCE
            eligible = False
        elif positive:
            disposition = ELIGIBLE_BOUNDED_PROPOSAL
            eligible = True
        else:
            disposition = STOP_NO_POSITIVE_EVIDENCE
            eligible = False

    return ProductGateReceipt(
        schema=VERSION,
        parent_heads=(PR671_HEAD, PR672_HEAD),
        parent_runs=(PR671_RUN, PR672_RUN),
        signal_count=len(signals),
        gate_count=len(gates),
        all_hard_gates_pass=feasible,
        failed_gate_ids=failed,
        blocker_set=blockers,
        evidence_policy_evaluated=evaluated,
        positive_evidence_present=positive,
        opposing_evidence_present=opposing,
        max_support_strength=max_support,
        disposition=disposition,
        bounded_proposal_eligible=eligible,
        evidence_can_compensate_for_failed_gate=False,
        evidence_magnitude_changes_feasibility=False,
        k27_coordinate_grants_constraint_satisfaction=False,
        semantic_truth_minted=False,
        effect_authority_granted=False,
        native_private_transformer_kv_accessed=False,
        gate10_promoted=False,
        merge_or_deployment_authorized=False,
    )


def current_parent_fixture(*, support_strength: int = 1) -> ProductGateReceipt:
    signal = EvidenceSignal(
        signal_id="pr671-official-equal-rate-canary",
        outcome=SUPPORTS,
        strength=support_strength,
        scope="GLM53_LAYER3_EXPERT0_8X64_TILE_EQUAL_RATE_MSE",
        evidence_digest="00bae035570665f19c40405c8d04002f894f6a7c05c75155ce9e63d8dcf9f01a",
    )
    gate = HardGate(
        gate_id="pr672-official-source-header-admission",
        passed=False,
        domain="OFFICIAL_SOURCE_C2_REQUEST_ADMISSION",
        blocker="OFFICIAL_INDEX_BYTES_AND_REPRESENTATIVE_HEADERS_NOT_MATERIALIZED",
    )
    return evaluate_product_gate(signals=(signal,), gates=(gate,))


def main() -> None:
    receipt = current_parent_fixture()
    body = asdict(receipt)
    body["receipt_digest"] = receipt.receipt_digest
    body["laws"] = (
        "PositiveEvidenceCannotPayHardGateDebt",
        "HardConstraint!=NegativeReward",
        "EvidenceMagnitude!=Feasibility",
        "OrthogonalEvidenceAxesDoNotCancel",
        "SourceGateDominatesRepresentationEnthusiasm",
        "K27Coordinate!=ConstraintSatisfaction!=SemanticAuthority",
    )
    print(json.dumps(body, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
