#!/usr/bin/env python3
"""Typed hard-gate transition admission for AuraOS / HyperScale.

This module owns only the relation between an already-valid non-compensatory
product gate and an exact evidence generation that changes one hard predicate
from FAIL to PASS. It deliberately does not own the gate, the evidence signal,
or any execution/effect authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Sequence

from tools import aura_noncompensatory_evidence_product_gate as n1

VERSION = "AURA_HARD_GATE_TRANSITION_ADMISSION_V1"
N1_HEAD = "9c0c548235397ab0cd774038468c8fe4c770d9fe"
N1_RUN = 33402556317
N1_JOB = 99522161582
Q15_HEAD = "9f3f37097b3e076b77f197728301c599074e2a3b"
Q15_RUN = 33402644106
Q15_JOB = 99522457067
Q15_RECEIPT = "5c40963d01ce137a8c7af89cd6854cdb8f5c46840c9143b2bde24d3bddb889b5"
CONVERGENCE = "eb3c1beedab41521754fbdf955957777c260d5fd"


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _digest(value: str) -> None:
    if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError("INVALID_SHA256_DIGEST")


@dataclass(frozen=True)
class EvidenceGeneration:
    signal: n1.EvidenceSignal
    generation: str

    @property
    def descriptor_digest(self) -> str:
        self.signal.validate()
        return _sha(asdict(self.signal))

    def validate(self) -> None:
        self.signal.validate()
        if not self.generation.strip():
            raise ValueError("EVIDENCE_GENERATION_REQUIRED")


@dataclass(frozen=True)
class GateEvidenceState:
    gate_id: str
    domain: str
    gate_scope_digest: str
    evidence_generation: str
    receipt_digest: str
    passed: bool
    blocker: str | None
    exact_green: bool

    def validate(self) -> None:
        if not self.gate_id.strip() or not self.domain.strip():
            raise ValueError("GATE_ID_AND_DOMAIN_REQUIRED")
        _digest(self.gate_scope_digest)
        _digest(self.receipt_digest)
        if not self.evidence_generation.strip():
            raise ValueError("GATE_EVIDENCE_GENERATION_REQUIRED")
        if type(self.passed) is not bool or type(self.exact_green) is not bool:
            raise ValueError("GATE_STATE_BOOLEANS_REQUIRED")
        if self.passed and self.blocker is not None:
            raise ValueError("PASSED_GATE_CANNOT_HAVE_BLOCKER")
        if not self.passed and (self.blocker is None or not self.blocker.strip()):
            raise ValueError("FAILED_GATE_REQUIRES_BLOCKER")

    def product_gate(self) -> n1.HardGate:
        return n1.HardGate(
            gate_id=self.gate_id,
            passed=self.passed,
            domain=self.domain,
            blocker=self.blocker,
        )


@dataclass(frozen=True)
class HardGateTransitionReceipt:
    schema: str
    parent_heads: tuple[str, str]
    parent_runs: tuple[int, int]
    parent_jobs: tuple[int, int]
    convergence_commit: str
    gate_id: str
    gate_scope_digest: str
    before_gate_generation: str
    after_gate_generation: str
    before_gate_receipt_digest: str
    closure_receipt_digest: str
    before_passed: bool
    after_passed: bool
    before_blocker: str
    evidence_descriptor_digest: str
    evidence_generation: str
    evidence_unchanged: bool
    changed_hard_gate_ids: tuple[str, ...]
    unchanged_hard_gate_ids: tuple[str, ...]
    before_product_receipt_digest: str
    after_product_receipt_digest: str
    before_product_feasible: bool
    after_product_feasible: bool
    before_disposition: str
    after_disposition: str
    evidence_policy_evaluated_before: bool
    evidence_policy_evaluated_after: bool
    bounded_proposal_eligible_after: bool
    minimum_affected_cone: tuple[str, ...]
    proposal_eligibility_grants_execution_authority: bool
    gate_closure_grants_tensor_payload_evidence: bool
    evidence_replay_counts_as_gate_closure: bool
    currentness_observation_counts_as_semantic_generation: bool
    k27_coordinate_affects_feasibility: bool
    semantic_truth_minted: bool
    effect_authority_granted: bool
    native_private_transformer_kv_accessed: bool
    gate10_promoted: bool
    merge_or_deployment_authorized: bool

    @property
    def receipt_digest(self) -> str:
        return _sha(asdict(self))


def admit_hard_gate_transition(
    *,
    before_gate: GateEvidenceState,
    after_gate: GateEvidenceState,
    before_evidence: EvidenceGeneration,
    after_evidence: EvidenceGeneration,
    unchanged_gates_before: Sequence[n1.HardGate] = (),
    unchanged_gates_after: Sequence[n1.HardGate] = (),
) -> HardGateTransitionReceipt:
    """Validate one exact hard-gate closure and recompute only its product cone."""
    before_gate.validate()
    after_gate.validate()
    before_evidence.validate()
    after_evidence.validate()

    if before_gate.gate_id != after_gate.gate_id:
        raise ValueError("GATE_ID_CHANGED")
    if before_gate.domain != after_gate.domain:
        raise ValueError("GATE_DOMAIN_CHANGED")
    if before_gate.gate_scope_digest != after_gate.gate_scope_digest:
        raise ValueError("GATE_SCOPE_CHANGED")
    if before_gate.evidence_generation == after_gate.evidence_generation:
        raise ValueError("GATE_EVIDENCE_GENERATION_DID_NOT_ADVANCE")
    if before_gate.passed or not after_gate.passed:
        raise ValueError("TRANSITION_MUST_BE_FAIL_TO_PASS")
    if not before_gate.exact_green:
        raise ValueError("BEFORE_GATE_RECEIPT_NOT_EXACT")
    if not after_gate.exact_green:
        raise ValueError("CLOSURE_RECEIPT_NOT_EXACT_GREEN_CURRENT")
    if before_evidence.descriptor_digest != after_evidence.descriptor_digest:
        raise ValueError("EVIDENCE_DESCRIPTOR_CHANGED_DURING_GATE_CLOSURE")
    if before_evidence.generation != after_evidence.generation:
        raise ValueError("EVIDENCE_GENERATION_CHANGED_DURING_GATE_CLOSURE")

    for gate in tuple(unchanged_gates_before) + tuple(unchanged_gates_after):
        gate.validate()
        if gate.gate_id == before_gate.gate_id:
            raise ValueError("TARGET_GATE_DUPLICATED_IN_UNCHANGED_SET")

    bmap = {g.gate_id: g for g in unchanged_gates_before}
    amap = {g.gate_id: g for g in unchanged_gates_after}
    if len(bmap) != len(unchanged_gates_before) or len(amap) != len(unchanged_gates_after):
        raise ValueError("DUPLICATE_UNCHANGED_GATE_ID")
    if set(bmap) != set(amap):
        raise ValueError("UNCHANGED_GATE_SET_CHANGED")
    for gid in sorted(bmap):
        if bmap[gid] != amap[gid]:
            raise ValueError("UNRECEIPTED_SECOND_GATE_CHANGE")

    before_product = n1.evaluate_product_gate(
        signals=(before_evidence.signal,),
        gates=(before_gate.product_gate(), *tuple(unchanged_gates_before)),
    )
    after_product = n1.evaluate_product_gate(
        signals=(after_evidence.signal,),
        gates=(after_gate.product_gate(), *tuple(unchanged_gates_after)),
    )
    if before_product.disposition != n1.HOLD_HARD_GATE:
        raise ValueError("BEFORE_STATE_NOT_HARD_GATE_HOLD")
    if before_product.evidence_policy_evaluated:
        raise ValueError("EVIDENCE_POLICY_EVALUATED_BEFORE_FEASIBILITY")

    unaffected = tuple(sorted(bmap))
    cone = (
        f"gate:{before_gate.gate_id}",
        "product-feasibility",
        "bounded-evidence-policy",
        "work-disposition",
    )
    return HardGateTransitionReceipt(
        schema=VERSION,
        parent_heads=(N1_HEAD, Q15_HEAD),
        parent_runs=(N1_RUN, Q15_RUN),
        parent_jobs=(N1_JOB, Q15_JOB),
        convergence_commit=CONVERGENCE,
        gate_id=before_gate.gate_id,
        gate_scope_digest=before_gate.gate_scope_digest,
        before_gate_generation=before_gate.evidence_generation,
        after_gate_generation=after_gate.evidence_generation,
        before_gate_receipt_digest=before_gate.receipt_digest,
        closure_receipt_digest=after_gate.receipt_digest,
        before_passed=False,
        after_passed=True,
        before_blocker=before_gate.blocker or "",
        evidence_descriptor_digest=before_evidence.descriptor_digest,
        evidence_generation=before_evidence.generation,
        evidence_unchanged=True,
        changed_hard_gate_ids=(before_gate.gate_id,),
        unchanged_hard_gate_ids=unaffected,
        before_product_receipt_digest=before_product.receipt_digest,
        after_product_receipt_digest=after_product.receipt_digest,
        before_product_feasible=before_product.all_hard_gates_pass,
        after_product_feasible=after_product.all_hard_gates_pass,
        before_disposition=before_product.disposition,
        after_disposition=after_product.disposition,
        evidence_policy_evaluated_before=before_product.evidence_policy_evaluated,
        evidence_policy_evaluated_after=after_product.evidence_policy_evaluated,
        bounded_proposal_eligible_after=after_product.bounded_proposal_eligible,
        minimum_affected_cone=cone,
        proposal_eligibility_grants_execution_authority=False,
        gate_closure_grants_tensor_payload_evidence=False,
        evidence_replay_counts_as_gate_closure=False,
        currentness_observation_counts_as_semantic_generation=False,
        k27_coordinate_affects_feasibility=False,
        semantic_truth_minted=False,
        effect_authority_granted=False,
        native_private_transformer_kv_accessed=False,
        gate10_promoted=False,
        merge_or_deployment_authorized=False,
    )


def current_n1_q15_fixture() -> HardGateTransitionReceipt:
    signal = n1.EvidenceSignal(
        signal_id="pr671-official-equal-rate-canary",
        outcome=n1.SUPPORTS,
        strength=1,
        scope="GLM53_LAYER3_EXPERT0_8X64_TILE_EQUAL_RATE_MSE",
        evidence_digest="00bae035570665f19c40405c8d04002f894f6a7c05c75155ce9e63d8dcf9f01a",
    )
    evidence = EvidenceGeneration(signal=signal, generation=n1.PR671_HEAD)
    scope_digest = _sha("OFFICIAL_SOURCE_C2_REQUEST_ADMISSION")
    before = GateEvidenceState(
        gate_id="pr672-official-source-header-admission",
        domain="OFFICIAL_SOURCE_C2_REQUEST_ADMISSION",
        gate_scope_digest=scope_digest,
        evidence_generation=n1.PR672_HEAD,
        receipt_digest=_sha({"head": n1.PR672_HEAD, "state": "HOLD", "blocker": "OFFICIAL_INDEX_BYTES_AND_REPRESENTATIVE_HEADERS_NOT_MATERIALIZED"}),
        passed=False,
        blocker="OFFICIAL_INDEX_BYTES_AND_REPRESENTATIVE_HEADERS_NOT_MATERIALIZED",
        exact_green=True,
    )
    after = GateEvidenceState(
        gate_id=before.gate_id,
        domain=before.domain,
        gate_scope_digest=scope_digest,
        evidence_generation=Q15_HEAD,
        receipt_digest=Q15_RECEIPT,
        passed=True,
        blocker=None,
        exact_green=True,
    )
    return admit_hard_gate_transition(
        before_gate=before,
        after_gate=after,
        before_evidence=evidence,
        after_evidence=evidence,
    )


def main() -> None:
    receipt = current_n1_q15_fixture()
    body = asdict(receipt)
    body["receipt_digest"] = receipt.receipt_digest
    body["laws"] = (
        "PositiveEvidenceCannotPayHardGateDebt",
        "GateClosureChangesFeasibilityOnlyThroughExactGateEvidenceGeneration",
        "GateTransition!=EvidenceGenerationAdvance",
        "EvidenceReplay!=GateClosure",
        "CurrentnessObservation!=SemanticGeneration",
        "OneGateClosed!=AllGatesClosed",
        "ProposalEligibility!=ExecutionAuthority",
        "MinimumAffectedConeAfterGateTransition",
        "K27Coordinate!=ConstraintSatisfaction!=SemanticAuthority",
    )
    print(json.dumps(body, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
