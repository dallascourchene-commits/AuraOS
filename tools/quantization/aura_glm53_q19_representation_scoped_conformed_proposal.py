#!/usr/bin/env python3
"""Q19: admit repaired Q6 evidence through Q17's conformed product-gate algebra.

Derivation parents:
- Q17 exact-green domain-router <-> generic product-gate conformance.
- Q6 repaired exact-green 2.25-bpw E8-vs-optimized-scalar official-source canary.

Q19 owns only representation-scoped proposal-basis admission. It deliberately does
not mutate Q18's distinct 1.25-bpw proposal, authorize execution, or generalize a
finite two-tile distortion observation.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from typing import Any

from tools import aura_noncompensatory_evidence_product_gate as n1

SCHEMA = "AURA_GLM53_Q19_REPRESENTATION_SCOPED_CONFORMED_PROPOSAL_V1"
Q6_SCHEMA = "AURA_GLM53_OFFICIAL_E8_VS_OPTIMIZED_SCALAR_CANARY_V2"

Q17_HEAD = "a6de82e18f9c296b6ec0c3f3b3ff75d8ad29dab5"
Q17_RUN = 33403753367
Q17_JOB = 99526112800
Q17_SOURCE_BLOB = "2734ca5fd9326fe730f196d6508d3bc5a7311f00"

Q6_SEMANTIC_HEAD = "6403210cba7992b91ea855151e18aa79c2677f84"
Q6_PROOF_HEAD = "f6c61d9d19dcc04367b69577ba9cda090e8cd655"
Q6_PROOF_RUN = 33404776198
Q6_PROOF_JOB = 99529516026
Q6_SOURCE_BLOB = "d1784822445d7109d28ffa1aebc013e3feb5be75"
Q6_RECEIPT_DIGEST = "5173b6c1df5f6f889a7912574c51beac546b09a92457cc32ba5918a8f6bd28a4"

S1_HEAD = "9dab15c3a0bb0b9ad2408fdd54b09cfcfa1373d8"
S1_RUN = 33403087858
Q18_OWNER_DRIVE_ID = "1ZRaZJt7hajtrTZGhmxsTSu6yx2SR6YZr8FfKxF8vZPo"
Q18_REPRESENTATIVE_EVIDENCE_HEAD = "dbdfad22555c78f84c6a203e20c0300b503448d7"

Q6_RATE_BPW = 2.25
Q6_SCOPE = "GLM53_Q6_2P25_CODEC_RATE_TWO_OFFICIAL_TILES"
OUTCOME_TO_SIGNAL = {
    "E8_WIN": n1.SUPPORTS,
    "TIE": n1.NEUTRAL,
    "SCALAR_WIN": n1.OPPOSES,
}


def _sha(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


def validate_q6_receipt(q6: dict[str, Any], *, require_exact_current: bool = False) -> None:
    if q6.get("schema") != Q6_SCHEMA:
        raise ValueError("Q6_SCHEMA_MISMATCH")
    rate = q6.get("exact_codec_rate_bpw")
    if type(rate) not in (int, float) or not math.isclose(float(rate), Q6_RATE_BPW, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError("Q6_CODEC_RATE_MISMATCH")
    if q6.get("codec_rate_domain_only") is not True:
        raise ValueError("Q6_CODEC_RATE_DOMAIN_REQUIRED")
    if q6.get("container_rate_comparison_claimed") is not False:
        raise ValueError("Q6_CONTAINER_RATE_CROSSCAST")
    if q6.get("same_official_source_tiles_compared") is not True:
        raise ValueError("Q6_SOURCE_SCOPE_NOT_EXACT")
    if q6.get("optimized_scalar_control_used") is not True:
        raise ValueError("Q6_SERIOUS_CONTROL_REQUIRED")
    if q6.get("official_source_equal_rate_distortion_evidence") is not True:
        raise ValueError("Q6_EQUAL_RATE_EVIDENCE_NOT_OBSERVED")
    if q6.get("representative_canary_scope_only") is not True:
        raise ValueError("Q6_SCOPE_CEILING_WIDENED")
    outcome = q6.get("aggregate_outcome")
    if outcome not in OUTCOME_TO_SIGNAL:
        raise ValueError("Q6_OUTCOME_INVALID")

    roles = q6.get("roles")
    if not isinstance(roles, list) or len(roles) != 2:
        raise ValueError("Q6_EXACT_TWO_ROLE_CANARIES_REQUIRED")
    for role in roles:
        if not isinstance(role, dict):
            raise ValueError("Q6_ROLE_RECORD_INVALID")
        if role.get("equal_codec_rate") is not True or role.get("equal_codec_payload_bytes") is not True:
            raise ValueError("Q6_ROLE_CODEC_RATE_PARITY_REQUIRED")
        if role.get("q14_e8_codec_payload_bytes") != 18 or role.get("scalar_codec_payload_bytes") != 18:
            raise ValueError("Q6_ROLE_EXACT_18_BYTE_CODEC_REQUIRED")
        if not math.isclose(float(role.get("q14_e8_codec_bits_per_weight", -1.0)), Q6_RATE_BPW, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError("Q6_ROLE_E8_CODEC_RATE_MISMATCH")
        if not math.isclose(float(role.get("scalar_codec_bits_per_weight", -1.0)), Q6_RATE_BPW, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError("Q6_ROLE_SCALAR_CODEC_RATE_MISMATCH")
        if role.get("container_rate_comparison_claimed") is not False:
            raise ValueError("Q6_ROLE_CONTAINER_RATE_CROSSCAST")
        if float(role.get("q14_e8_serialized_bits_per_weight", 0.0)) <= Q6_RATE_BPW:
            raise ValueError("Q6_ROLE_CONTAINER_DOMAIN_NOT_DISTINCT")
        if role.get("outcome") not in OUTCOME_TO_SIGNAL:
            raise ValueError("Q6_ROLE_OUTCOME_INVALID")

    for key in (
        "geometry_privileged", "full_role_quantized", "whole_model_quantized",
        "glm_quality_proven", "runtime_performance_proven", "semantic_k27_authority",
        "native_private_transformer_kv_accessed", "gate10_promoted",
    ):
        if q6.get(key) is not False:
            raise ValueError(f"Q6_CLAIM_CEILING_WIDENED:{key}")

    if require_exact_current and q6.get("receipt_digest") != Q6_RECEIPT_DIGEST:
        raise ValueError("Q6_RECEIPT_DIGEST_MISMATCH")


@dataclass(frozen=True)
class RepresentationScopedConformedProposalReceipt:
    schema: str
    q17_head: str
    q17_run: int
    q17_job: int
    q6_semantic_head: str
    q6_proof_head: str
    q6_proof_run: int
    q6_proof_job: int
    q6_receipt_digest: str
    source_gate_generation: str
    source_gate_passed: bool
    source_blocker: str | None
    representation_scope: str
    q6_representation_scheme: str
    scalar_scheme: str
    exact_codec_rate_bpw: float
    codec_rate_domain_only: bool
    container_rate_comparison_claimed: bool
    representative_outcome: str
    generic_disposition: str
    proposal_eligible: bool
    representation_identity_digest: str
    proposal_basis_digest: str | None
    q18_owner_drive_id: str
    q18_1p25_proposal_mutated: bool
    q18_evidence_crosscast_into_q19: bool
    full_tensor_or_model_scope_granted: bool
    model_quality_proven: bool
    runtime_performance_proven: bool
    execution_authority_granted: bool
    effect_authority_granted: bool
    semantic_k27_authority_minted: bool
    native_private_transformer_kv_accessed: bool
    gate10_promoted: bool
    merge_or_deployment_authorized: bool
    reason: str

    @property
    def receipt_digest(self) -> str:
        return _sha(asdict(self))


def admit_representation_scoped_proposal(
    q6: dict[str, Any],
    *,
    source_gate_passed: bool,
    source_gate_generation: str,
    source_blocker: str | None = None,
    require_exact_current: bool = False,
) -> RepresentationScopedConformedProposalReceipt:
    validate_q6_receipt(q6, require_exact_current=require_exact_current)
    if type(source_gate_passed) is not bool:
        raise ValueError("SOURCE_GATE_BOOL_REQUIRED")
    if not isinstance(source_gate_generation, str) or not source_gate_generation:
        raise ValueError("SOURCE_GATE_GENERATION_REQUIRED")
    if require_exact_current and source_gate_generation != S1_HEAD:
        raise ValueError("SOURCE_GATE_GENERATION_NOT_EXACT_S1")
    if source_gate_passed and source_blocker is not None:
        raise ValueError("PASSED_SOURCE_GATE_CANNOT_HAVE_BLOCKER")
    if not source_gate_passed and not source_blocker:
        raise ValueError("FAILED_SOURCE_GATE_REQUIRES_BLOCKER")

    outcome = str(q6["aggregate_outcome"])
    signal = n1.EvidenceSignal(
        signal_id="glm53-q19-q6-2p25-e8-vs-optimized-scalar",
        outcome=OUTCOME_TO_SIGNAL[outcome],
        strength=1,
        scope=Q6_SCOPE,
        evidence_digest=str(q6.get("receipt_digest", "0" * 64)),
    )
    gate = n1.HardGate(
        gate_id="glm53-q19-source-c2-admission",
        passed=source_gate_passed,
        domain="OFFICIAL_SOURCE_C2_REQUEST_ADMISSION",
        blocker=None if source_gate_passed else source_blocker,
    )
    generic = n1.evaluate_product_gate(signals=(signal,), gates=(gate,))

    representation_identity = _sha({
        "scope": Q6_SCOPE,
        "official_repository": q6.get("official_repository"),
        "official_revision": q6.get("official_revision"),
        "layer": q6.get("selected_layer"),
        "expert": q6.get("selected_expert"),
        "q14_canary_page_set_digest": q6.get("q14_canary_page_set_digest"),
        "q14_representation_scheme": q6.get("q14_representation_scheme"),
        "scalar_scheme": q6.get("scalar_scheme"),
        "scalar_representation_digest": q6.get("scalar_representation_digest"),
        "codec_rate_bpw": Q6_RATE_BPW,
        "accounting_domain": "CODEC_PAYLOAD_ONLY",
    })
    proposal_basis = None
    if generic.bounded_proposal_eligible:
        proposal_basis = _sha({
            "q17_head": Q17_HEAD,
            "q6_receipt_digest": q6.get("receipt_digest"),
            "source_gate_generation": source_gate_generation,
            "representation_identity_digest": representation_identity,
            "generic_disposition": generic.disposition,
        })

    reason = {
        n1.HOLD_HARD_GATE: "HOLD_SOURCE_GATE",
        n1.ELIGIBLE_BOUNDED_PROPOSAL: "REPRESENTATION_SCOPED_BOUNDED_PROPOSAL_ELIGIBLE",
        n1.STOP_NO_POSITIVE_EVIDENCE: "STOP_NO_REPRESENTATIVE_ADVANTAGE_TIE",
        n1.STOP_OPPOSING_EVIDENCE: "STOP_REPRESENTATIVE_ADVANTAGE_OPPOSED",
    }.get(generic.disposition, "UNEXPECTED_GENERIC_DISPOSITION")

    return RepresentationScopedConformedProposalReceipt(
        schema=SCHEMA,
        q17_head=Q17_HEAD,
        q17_run=Q17_RUN,
        q17_job=Q17_JOB,
        q6_semantic_head=Q6_SEMANTIC_HEAD,
        q6_proof_head=Q6_PROOF_HEAD,
        q6_proof_run=Q6_PROOF_RUN,
        q6_proof_job=Q6_PROOF_JOB,
        q6_receipt_digest=str(q6.get("receipt_digest", "")),
        source_gate_generation=source_gate_generation,
        source_gate_passed=source_gate_passed,
        source_blocker=source_blocker,
        representation_scope=Q6_SCOPE,
        q6_representation_scheme=str(q6.get("q14_representation_scheme")),
        scalar_scheme=str(q6.get("scalar_scheme")),
        exact_codec_rate_bpw=Q6_RATE_BPW,
        codec_rate_domain_only=True,
        container_rate_comparison_claimed=False,
        representative_outcome=outcome,
        generic_disposition=generic.disposition,
        proposal_eligible=generic.bounded_proposal_eligible,
        representation_identity_digest=representation_identity,
        proposal_basis_digest=proposal_basis,
        q18_owner_drive_id=Q18_OWNER_DRIVE_ID,
        q18_1p25_proposal_mutated=False,
        q18_evidence_crosscast_into_q19=False,
        full_tensor_or_model_scope_granted=False,
        model_quality_proven=False,
        runtime_performance_proven=False,
        execution_authority_granted=False,
        effect_authority_granted=False,
        semantic_k27_authority_minted=False,
        native_private_transformer_kv_accessed=False,
        gate10_promoted=False,
        merge_or_deployment_authorized=False,
        reason=reason,
    )


def main() -> None:
    raise SystemExit("Q19 requires an explicit repaired Q6 receipt and source-gate generation.")


__all__ = [
    "RepresentationScopedConformedProposalReceipt",
    "admit_representation_scoped_proposal",
    "validate_q6_receipt",
]
