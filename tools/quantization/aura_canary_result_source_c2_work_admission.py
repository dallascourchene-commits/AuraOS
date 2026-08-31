#!/usr/bin/env python3
"""Join bounded official quantization evidence to source-bound C2 work admission.

This module is a work-routing membrane, not an execution or scientific-truth owner.
It keeps a favorable representative distortion result subordinate to the current
source/header request-admission gate.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
import re

SCHEMA = "AURA_CANARY_RESULT_SOURCE_C2_WORK_ADMISSION_V1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ALLOWED_OUTCOMES = {"E8_WIN", "CONTROL_WIN", "TIE"}

Q5_HEAD = "23c8345a1e3d5034ce88bea1ab32c69c1a9cf3f2"
Q5_RUN = 33400399223
Q5_RECEIPT_DIGEST = "00bae035570665f19c40405c8d04002f894f6a7c05c75155ce9e63d8dcf9f01a"
Q5_SOURCE_BLOB = "5b39ce1132f8ef520529487411628be04e51f32a"
Q7_HEAD = "7340091202f3f1a859841c3ec4314191f18fa1ad"
Q7_RUN = 33400557094
Q7_DISPOSITION_DIGEST = "1ce62706145c7ba181ff2e40d6f2340fc21e08191c137641b68135acf44e6a1f"
Q7_SOURCE_BLOB = "31837eb716139170cbdd5290f7aae889cd7b90be"
OFFICIAL_REPOSITORY = "zai-org/GLM-5.3"
OFFICIAL_REVISION = "7cda81930d6e4cef42f48555de830aa32ecdde28"
Q13_SOURCE_SET_DIGEST = "f41495beb566f4c49f5674f2820f3d5c32591647be552048cf711a885a1b71b6"


def _sha(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _require_sha(name: str, value: str) -> None:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise ValueError(f"{name} must be lowercase SHA-256")


@dataclass(frozen=True)
class RepresentativeCanaryEvidence:
    producer_head: str
    producer_run: int
    receipt_digest: str
    official_repository: str
    official_revision: str
    source_set_digest: str
    total_weights: int
    tile_count: int
    candidate_bpw: float
    control_bpw: float
    aggregate_candidate_mse: float
    aggregate_control_mse: float
    aggregate_outcome: str
    representative_scope_only: bool
    geometry_privileged: bool
    full_tensor_quantized: bool
    whole_model_quantized: bool
    quality_proven: bool
    runtime_performance_proven: bool

    def validate(self) -> None:
        if self.producer_head != Q5_HEAD or self.producer_run != Q5_RUN:
            raise ValueError("Q5_PRODUCER_GENERATION_MISMATCH")
        if self.receipt_digest != Q5_RECEIPT_DIGEST:
            raise ValueError("Q5_RECEIPT_IDENTITY_MISMATCH")
        if self.official_repository != OFFICIAL_REPOSITORY or self.official_revision != OFFICIAL_REVISION:
            raise ValueError("Q5_OFFICIAL_SOURCE_MISMATCH")
        if self.source_set_digest != Q13_SOURCE_SET_DIGEST:
            raise ValueError("Q5_SOURCE_SET_MISMATCH")
        if self.total_weights != 512 or self.tile_count != 8:
            raise ValueError("Q5_REPRESENTATIVE_SCOPE_MISMATCH")
        if self.candidate_bpw != 1.25 or self.control_bpw != 1.25:
            raise ValueError("Q5_EQUAL_RATE_DRIFT")
        if not math.isfinite(self.aggregate_candidate_mse) or self.aggregate_candidate_mse < 0:
            raise ValueError("Q5_CANDIDATE_MSE_INVALID")
        if not math.isfinite(self.aggregate_control_mse) or self.aggregate_control_mse < 0:
            raise ValueError("Q5_CONTROL_MSE_INVALID")
        if self.aggregate_outcome not in ALLOWED_OUTCOMES:
            raise ValueError("Q5_OUTCOME_INVALID")
        derived = (
            "E8_WIN" if self.aggregate_candidate_mse < self.aggregate_control_mse
            else "CONTROL_WIN" if self.aggregate_candidate_mse > self.aggregate_control_mse
            else "TIE"
        )
        if self.aggregate_outcome != derived:
            raise ValueError("Q5_OUTCOME_MSE_CONTRADICTION")
        if not self.representative_scope_only:
            raise ValueError("Q5_SCOPE_CEILING_WIDENED")
        if any((
            self.geometry_privileged,
            self.full_tensor_quantized,
            self.whole_model_quantized,
            self.quality_proven,
            self.runtime_performance_proven,
        )):
            raise ValueError("Q5_CLAIM_CEILING_WIDENED")


@dataclass(frozen=True)
class SourceBoundC2Disposition:
    producer_head: str
    producer_run: int
    disposition_digest: str
    official_repository: str
    official_revision: str
    request_source_matches: bool
    source_header_trial_eligible: bool
    source_tensor_payload_bound: bool
    real_tensor_quantization_eligible: bool
    source_bound_c2_request_admissible: bool
    blocker: str
    execution_authorized: bool
    owner_host_execution_observed: bool
    physical_io_attested: bool
    g2_admitted: bool

    def validate(self) -> None:
        if self.producer_head != Q7_HEAD or self.producer_run != Q7_RUN:
            raise ValueError("Q7_PRODUCER_GENERATION_MISMATCH")
        if self.disposition_digest != Q7_DISPOSITION_DIGEST:
            raise ValueError("Q7_DISPOSITION_IDENTITY_MISMATCH")
        if self.official_repository != OFFICIAL_REPOSITORY or self.official_revision != OFFICIAL_REVISION:
            raise ValueError("Q7_OFFICIAL_SOURCE_MISMATCH")
        if not self.request_source_matches:
            raise ValueError("Q7_C2_REQUEST_SOURCE_MISMATCH")
        if any((
            self.source_tensor_payload_bound,
            self.real_tensor_quantization_eligible,
            self.execution_authorized,
            self.owner_host_execution_observed,
            self.physical_io_attested,
            self.g2_admitted,
        )):
            raise ValueError("Q7_AUTHORITY_OR_EFFECT_WIDENING")
        if self.source_bound_c2_request_admissible and not self.source_header_trial_eligible:
            raise ValueError("Q7_REQUEST_ADMISSION_WITHOUT_HEADER_ELIGIBILITY")
        if not self.source_bound_c2_request_admissible and not self.blocker:
            raise ValueError("Q7_HOLD_REQUIRES_BLOCKER")


def admit_canary_result_to_c2_work(
    canary: RepresentativeCanaryEvidence,
    source_c2: SourceBoundC2Disposition,
) -> dict[str, object]:
    canary.validate()
    source_c2.validate()
    if canary.official_repository != source_c2.official_repository or canary.official_revision != source_c2.official_revision:
        raise ValueError("CROSS_PARENT_OFFICIAL_SOURCE_MISMATCH")

    if not source_c2.source_bound_c2_request_admissible:
        disposition = "SOURCE_ADMISSION_HOLD"
        reason = source_c2.blocker
        c2_request_proposal_eligible = False
    elif canary.aggregate_outcome == "E8_WIN":
        disposition = "BOUNDED_REPRESENTATIVE_E8_C2_REQUEST_PROPOSAL_ELIGIBLE"
        reason = "REPRESENTATIVE_EQUAL_RATE_E8_ADVANTAGE_AND_SOURCE_REQUEST_GATE_GREEN"
        c2_request_proposal_eligible = True
    else:
        disposition = "STOP_E8_ESCALATION_NO_REPRESENTATIVE_ADVANTAGE"
        reason = f"REPRESENTATIVE_{canary.aggregate_outcome}"
        c2_request_proposal_eligible = False

    body: dict[str, object] = {
        "schema": SCHEMA,
        "exact_other_agent_heads": [Q5_HEAD, Q7_HEAD],
        "exact_other_agent_runs": [Q5_RUN, Q7_RUN],
        "q5_receipt_digest": canary.receipt_digest,
        "q7_disposition_digest": source_c2.disposition_digest,
        "official_repository": OFFICIAL_REPOSITORY,
        "official_revision": OFFICIAL_REVISION,
        "source_set_digest": canary.source_set_digest,
        "representative_outcome": canary.aggregate_outcome,
        "representative_e8_over_control": (
            canary.aggregate_candidate_mse / canary.aggregate_control_mse
            if canary.aggregate_control_mse else None
        ),
        "source_header_trial_eligible": source_c2.source_header_trial_eligible,
        "source_bound_c2_request_admissible": source_c2.source_bound_c2_request_admissible,
        "disposition": disposition,
        "reason": reason,
        "c2_request_proposal_eligible": c2_request_proposal_eligible,
        "representative_evidence_preserved": True,
        "representative_evidence_only": True,
        "scientific_outcome_is_not_effect_authority": True,
        "source_tensor_payload_bound": False,
        "real_tensor_quantization_eligible": False,
        "execution_authorized": False,
        "owner_host_execution_observed": False,
        "physical_io_attested": False,
        "quality_superiority_proven": False,
        "runtime_superiority_proven": False,
        "full_tensor_superiority_proven": False,
        "whole_model_superiority_proven": False,
        "g2_admitted": False,
        "gate10_promoted": False,
        "semantic_k27_authority": False,
        "native_private_transformer_kv_accessed": False,
        "laws": [
            "FavorableRepresentativeEvidence!=ExecutionAuthority",
            "RepresentativeWin+SourceAdmissionHold=>Hold",
            "ScientificOutcome!=WorkAdmission",
            "SourceHeaderEligible!=TensorPayloadBound!=ExecutionAuthorized",
            "SourceGateDominatesRepresentationEnthusiasm",
            "BoundedWorkProposal!=OwnerHostExecutionObserved",
            "K27Coordinate!=SourceAuthority!=EffectAuthority",
        ],
    }
    body["receipt_digest"] = _sha(body)
    return body


def current_q5_fixture() -> RepresentativeCanaryEvidence:
    return RepresentativeCanaryEvidence(
        producer_head=Q5_HEAD,
        producer_run=Q5_RUN,
        receipt_digest=Q5_RECEIPT_DIGEST,
        official_repository=OFFICIAL_REPOSITORY,
        official_revision=OFFICIAL_REVISION,
        source_set_digest=Q13_SOURCE_SET_DIGEST,
        total_weights=512,
        tile_count=8,
        candidate_bpw=1.25,
        control_bpw=1.25,
        aggregate_candidate_mse=1.934803016678301e-05,
        aggregate_control_mse=3.1101250336599024e-05,
        aggregate_outcome="E8_WIN",
        representative_scope_only=True,
        geometry_privileged=False,
        full_tensor_quantized=False,
        whole_model_quantized=False,
        quality_proven=False,
        runtime_performance_proven=False,
    )


def current_q7_fixture() -> SourceBoundC2Disposition:
    return SourceBoundC2Disposition(
        producer_head=Q7_HEAD,
        producer_run=Q7_RUN,
        disposition_digest=Q7_DISPOSITION_DIGEST,
        official_repository=OFFICIAL_REPOSITORY,
        official_revision=OFFICIAL_REVISION,
        request_source_matches=True,
        source_header_trial_eligible=False,
        source_tensor_payload_bound=False,
        real_tensor_quantization_eligible=False,
        source_bound_c2_request_admissible=False,
        blocker="OFFICIAL_INDEX_BYTES_AND_REPRESENTATIVE_HEADERS_NOT_MATERIALIZED",
        execution_authorized=False,
        owner_host_execution_observed=False,
        physical_io_attested=False,
        g2_admitted=False,
    )


def main() -> None:
    print(json.dumps(admit_canary_result_to_c2_work(current_q5_fixture(), current_q7_fixture()), sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
