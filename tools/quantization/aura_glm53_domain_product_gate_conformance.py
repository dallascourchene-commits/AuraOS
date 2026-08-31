#!/usr/bin/env python3
"""Q17: prove the GLM-specific C2 router refines Aura's generic product gate.

PR674 owns the GLM-specific scientific-result -> source-C2 routing semantics.
PR677 owns the reusable non-compensatory hard-gate algebra. Q17 owns only their
conformance relation so policy cannot silently fork.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any

from tools import aura_noncompensatory_evidence_product_gate as n1

SCHEMA = "AURA_GLM53_DOMAIN_PRODUCT_GATE_CONFORMANCE_V1"

Q8_HEAD = "0db00cd19e98117f5f21e41afb218517f2d40dca"
Q8_RUN = 33402413489
Q8_JOB = 99521697092
Q8_WORKFLOW = "Aura Canary Result Source C2 Work Admission"
Q8_SOURCE_BLOB = "9a6e5d0d6855ab74e24d581e1bdbc7a2105c9144"
Q8_RECEIPT_DIGEST = "f6a4125c5d4769423c046c33ac17750531c3ed7e9ed53b20aed9e49b0cbb0a46"

N1_HEAD = "9c0c548235397ab0cd774038468c8fe4c770d9fe"
N1_RUN = 33402556317
N1_JOB = 99522161582
N1_WORKFLOW = "Aura Non-Compensatory Evidence Product Gate"
N1_SOURCE_BLOB = "c80bc8ae59468aad3dea020ac76f32c967444818"

OUTCOME_TO_SIGNAL = {
    "E8_WIN": n1.SUPPORTS,
    "TIE": n1.NEUTRAL,
    "CONTROL_WIN": n1.OPPOSES,
}
EXPECTED_DOMAIN_TO_GENERIC = {
    "SOURCE_ADMISSION_HOLD": n1.HOLD_HARD_GATE,
    "BOUNDED_REPRESENTATIVE_E8_C2_REQUEST_PROPOSAL_ELIGIBLE": n1.ELIGIBLE_BOUNDED_PROPOSAL,
    "STOP_E8_ESCALATION_NO_REPRESENTATIVE_ADVANTAGE:TIE": n1.STOP_NO_POSITIVE_EVIDENCE,
    "STOP_E8_ESCALATION_NO_REPRESENTATIVE_ADVANTAGE:CONTROL_WIN": n1.STOP_OPPOSING_EVIDENCE,
}


def _sha(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class DomainProductGateConformanceReceipt:
    schema: str
    q8_head: str
    q8_run: int
    q8_job: int
    q8_receipt_digest: str
    n1_head: str
    n1_run: int
    n1_job: int
    representative_outcome: str
    source_gate_passed: bool
    source_blocker: str | None
    q8_disposition: str
    n1_disposition: str
    q8_proposal_eligible: bool
    n1_proposal_eligible: bool
    disposition_mapping_exact: bool
    proposal_mapping_exact: bool
    blocker_mapping_exact: bool
    domain_router_refines_generic_product_gate: bool
    favorable_evidence_can_bypass_failed_source_gate: bool
    domain_policy_can_compensate_hard_gate: bool
    generic_policy_can_compensate_hard_gate: bool
    semantic_truth_minted: bool
    effect_authority_granted: bool
    native_private_transformer_kv_accessed: bool
    semantic_k27_authority_minted: bool
    gate10_promoted: bool
    merge_or_deployment_authorized: bool
    reason: str

    @property
    def receipt_digest(self) -> str:
        return _sha(asdict(self))


def validate_q8_receipt(q8: dict[str, Any], *, require_exact_current: bool = False) -> None:
    if q8.get("schema") != "AURA_CANARY_RESULT_SOURCE_C2_WORK_ADMISSION_V1":
        raise ValueError("Q8_SCHEMA_MISMATCH")
    outcome = q8.get("representative_outcome")
    if outcome not in OUTCOME_TO_SIGNAL:
        raise ValueError("Q8_OUTCOME_INVALID")
    if type(q8.get("source_bound_c2_request_admissible")) is not bool:
        raise ValueError("Q8_SOURCE_GATE_BOOL_REQUIRED")
    if type(q8.get("c2_request_proposal_eligible")) is not bool:
        raise ValueError("Q8_PROPOSAL_BOOL_REQUIRED")
    if q8.get("representative_evidence_only") is not True:
        raise ValueError("Q8_SCOPE_CEILING_WIDENED")
    for key in (
        "source_tensor_payload_bound", "real_tensor_quantization_eligible",
        "execution_authorized", "owner_host_execution_observed", "physical_io_attested",
        "quality_superiority_proven", "runtime_superiority_proven",
        "full_tensor_superiority_proven", "whole_model_superiority_proven",
        "g2_admitted", "gate10_promoted", "semantic_k27_authority",
        "native_private_transformer_kv_accessed",
    ):
        if q8.get(key) is not False:
            raise ValueError(f"Q8_CLAIM_CEILING_WIDENED:{key}")
    if require_exact_current:
        if q8.get("receipt_digest") != Q8_RECEIPT_DIGEST:
            raise ValueError("Q8_RECEIPT_DIGEST_MISMATCH")
        if q8.get("exact_other_agent_heads") != [
            "23c8345a1e3d5034ce88bea1ab32c69c1a9cf3f2",
            "7340091202f3f1a859841c3ec4314191f18fa1ad",
        ]:
            raise ValueError("Q8_PARENT_HEADS_MISMATCH")
        if q8.get("exact_other_agent_runs") != [33400399223, 33400557094]:
            raise ValueError("Q8_PARENT_RUNS_MISMATCH")


def _expected_generic_disposition(q8: dict[str, Any]) -> str:
    if not q8["source_bound_c2_request_admissible"]:
        return EXPECTED_DOMAIN_TO_GENERIC["SOURCE_ADMISSION_HOLD"]
    if q8["representative_outcome"] == "E8_WIN":
        return EXPECTED_DOMAIN_TO_GENERIC["BOUNDED_REPRESENTATIVE_E8_C2_REQUEST_PROPOSAL_ELIGIBLE"]
    return EXPECTED_DOMAIN_TO_GENERIC[
        f"STOP_E8_ESCALATION_NO_REPRESENTATIVE_ADVANTAGE:{q8['representative_outcome']}"
    ]


def prove_conformance(q8: dict[str, Any], *, require_exact_current: bool = False) -> DomainProductGateConformanceReceipt:
    validate_q8_receipt(q8, require_exact_current=require_exact_current)
    outcome = str(q8["representative_outcome"])
    gate_passed = bool(q8["source_bound_c2_request_admissible"])
    blocker = None if gate_passed else str(q8.get("reason") or "")
    if not gate_passed and not blocker:
        raise ValueError("Q8_FAILED_SOURCE_GATE_REQUIRES_BLOCKER")

    signal = n1.EvidenceSignal(
        signal_id="glm53-q8-representative-outcome",
        outcome=OUTCOME_TO_SIGNAL[outcome],
        strength=1,
        scope="GLM53_REPRESENTATIVE_EQUAL_RATE_CANARY",
        evidence_digest=str(q8.get("q5_receipt_digest", "0" * 64)),
    )
    gate = n1.HardGate(
        gate_id="glm53-q8-source-c2-admission",
        passed=gate_passed,
        domain="OFFICIAL_SOURCE_C2_REQUEST_ADMISSION",
        blocker=None if gate_passed else blocker,
    )
    generic = n1.evaluate_product_gate(signals=(signal,), gates=(gate,))

    expected_generic = _expected_generic_disposition(q8)
    disposition_exact = generic.disposition == expected_generic
    proposal_exact = bool(q8["c2_request_proposal_eligible"]) == generic.bounded_proposal_eligible
    blocker_exact = True if gate_passed else blocker in generic.blocker_set

    if not gate_passed:
        domain_expected = q8.get("disposition") == "SOURCE_ADMISSION_HOLD"
    elif outcome == "E8_WIN":
        domain_expected = q8.get("disposition") == "BOUNDED_REPRESENTATIVE_E8_C2_REQUEST_PROPOSAL_ELIGIBLE"
    else:
        domain_expected = q8.get("disposition") == "STOP_E8_ESCALATION_NO_REPRESENTATIVE_ADVANTAGE"

    refines = bool(domain_expected and disposition_exact and proposal_exact and blocker_exact)
    reason = "DOMAIN_ROUTER_REFINES_GENERIC_PRODUCT_GATE" if refines else "DOMAIN_GENERIC_POLICY_DIVERGENCE"

    return DomainProductGateConformanceReceipt(
        schema=SCHEMA,
        q8_head=Q8_HEAD,
        q8_run=Q8_RUN,
        q8_job=Q8_JOB,
        q8_receipt_digest=str(q8.get("receipt_digest", "")),
        n1_head=N1_HEAD,
        n1_run=N1_RUN,
        n1_job=N1_JOB,
        representative_outcome=outcome,
        source_gate_passed=gate_passed,
        source_blocker=blocker,
        q8_disposition=str(q8.get("disposition")),
        n1_disposition=generic.disposition,
        q8_proposal_eligible=bool(q8["c2_request_proposal_eligible"]),
        n1_proposal_eligible=generic.bounded_proposal_eligible,
        disposition_mapping_exact=disposition_exact,
        proposal_mapping_exact=proposal_exact,
        blocker_mapping_exact=blocker_exact,
        domain_router_refines_generic_product_gate=refines,
        favorable_evidence_can_bypass_failed_source_gate=False,
        domain_policy_can_compensate_hard_gate=False,
        generic_policy_can_compensate_hard_gate=generic.evidence_can_compensate_for_failed_gate,
        semantic_truth_minted=False,
        effect_authority_granted=False,
        native_private_transformer_kv_accessed=False,
        semantic_k27_authority_minted=False,
        gate10_promoted=False,
        merge_or_deployment_authorized=False,
        reason=reason,
    )


def main() -> None:
    raise SystemExit("Q17 requires an explicit Q8 receipt; use prove_conformance().")


__all__ = ["DomainProductGateConformanceReceipt", "prove_conformance", "validate_q8_receipt"]
