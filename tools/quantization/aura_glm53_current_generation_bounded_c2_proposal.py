#!/usr/bin/env python3
"""Bind current representative E8 evidence and current source admission to bounded C2 proposal eligibility.

Q18 is a routing/currentness membrane only. It deliberately consumes exactly two
current other-agent evidence generations (Q16 + S1) and pins PR674 only as the
historical policy substrate. It does not grant execution or effect authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re

SCHEMA = "AURA_GLM53_CURRENT_GENERATION_BOUNDED_C2_PROPOSAL_V1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

OFFICIAL_REPOSITORY = "zai-org/GLM-5.3"
OFFICIAL_REVISION = "7cda81930d6e4cef42f48555de830aa32ecdde28"
SOURCE_SET_DIGEST = "f41495beb566f4c49f5674f2820f3d5c32591647be552048cf711a885a1b71b6"

Q16_HEAD = "dbdfad22555c78f84c6a203e20c0300b503448d7"
Q16_RUN = 33403013214
Q16_JOB = 99523673267
Q16_ARTIFACT_ID = 9762051329
Q16_ARTIFACT_ZIP_SHA256 = "edaf31905c50e0a10b76ea215ad323050752b6637605e465e25b8fb43699fa61"
Q16_RECEIPT = "752ffc1d678294162b0688be896a14a9710a214280da6b489d21be50dfa0dfec"
Q16_SCOPE_ADMISSION_RECEIPT = "8c498a27f15e5355c197663b18fdaae405f933909ac67dccf50d10ed7fa6aca2"
Q5_RECEIPT = "00bae035570665f19c40405c8d04002f894f6a7c05c75155ce9e63d8dcf9f01a"

S1_HEAD = "9dab15c3a0bb0b9ad2408fdd54b09cfcfa1373d8"
S1_RUN = 33403087858
S1_JOB = 99523917975
S1_ARTIFACT_ID = 9762044001
S1_ARTIFACT_ZIP_SHA256 = "55681db1241c439302f595acbdf66c845d7e2b09d3b5040d5a05d7a237e9ad36"
S1_RECEIPT = "8f62629419578a84f0999de73186ba1971465cf673dc974a1066232af06ead1e"
S1_SOURCE_ADMISSION_DIGEST = "b24d831001b51f40c52e86f6632a0fdcc8bd3fbe040e35468610460c3e3b96b0"
S1_C2_REQUEST_DIGEST = "40c2ddff063fec238e3af14577426f5d0f938e38437ed00c44b3f2ec15d5eb33"
S1_INDEX_SHA256 = "e0fe7f28c1f853d4824e4d796374e3dacf1fe470988773952c79b063768134bf"
S1_HEADER_SHA256 = "ce48bcffe7bb48934e25adc5abc87d33f6e1280c6dc5ae0482a6963ee8e36027"

PR674_POLICY_HEAD = "0db00cd19e98117f5f21e41afb218517f2d40dca"
PR674_POLICY_BLOB = "9a6e5d0d6855ab74e24d581e1bdbc7a2105c9144"
LEGACY_Q7_HEAD = "7340091202f3f1a859841c3ec4314191f18fa1ad"
LEGACY_Q7_DISPOSITION_DIGEST = "1ce62706145c7ba181ff2e40d6f2340fc21e08191c137641b68135acf44e6a1f"

ELIGIBLE = "BOUNDED_REPRESENTATIVE_E8_C2_REQUEST_PROPOSAL_ELIGIBLE"


def _sha(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _require_sha(name: str, value: str) -> None:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise ValueError(f"{name}_INVALID_SHA256")


@dataclass(frozen=True)
class RepresentativeGeneration:
    producer_head: str
    producer_run: int
    producer_job: int
    artifact_id: int
    artifact_zip_sha256: str
    receipt_digest: str
    scope_admission_receipt: str
    q5_receipt_digest: str
    official_repository: str
    official_revision: str
    source_set_digest: str
    representative_scope_complete: bool
    minimum_missing_evidence_cone: tuple[str, ...]
    aggregate_outcome: str
    aggregate_e8_over_control: float
    candidate_bpw: float
    control_bpw: float
    total_official_weights: int
    tile_count: int

    def validate(self) -> None:
        expected = (Q16_HEAD, Q16_RUN, Q16_JOB, Q16_ARTIFACT_ID)
        if (self.producer_head, self.producer_run, self.producer_job, self.artifact_id) != expected:
            raise ValueError("Q16_GENERATION_IDENTITY_MISMATCH")
        for name, got, expected_digest in (
            ("Q16_ARTIFACT", self.artifact_zip_sha256, Q16_ARTIFACT_ZIP_SHA256),
            ("Q16_RECEIPT", self.receipt_digest, Q16_RECEIPT),
            ("Q16_SCOPE_RECEIPT", self.scope_admission_receipt, Q16_SCOPE_ADMISSION_RECEIPT),
            ("Q5_RECEIPT", self.q5_receipt_digest, Q5_RECEIPT),
            ("SOURCE_SET", self.source_set_digest, SOURCE_SET_DIGEST),
        ):
            _require_sha(name, got)
            if got != expected_digest:
                raise ValueError(f"{name}_MISMATCH")
        if (self.official_repository, self.official_revision) != (OFFICIAL_REPOSITORY, OFFICIAL_REVISION):
            raise ValueError("Q16_OFFICIAL_SOURCE_MISMATCH")
        if not self.representative_scope_complete or self.minimum_missing_evidence_cone:
            raise ValueError("Q16_REPRESENTATIVE_SCOPE_INCOMPLETE")
        if self.aggregate_outcome != "E8_WIN":
            raise ValueError("Q16_REPRESENTATIVE_OUTCOME_NOT_E8_WIN")
        if self.aggregate_e8_over_control != 0.6220981458103897:
            raise ValueError("Q16_AGGREGATE_RATIO_DRIFT")
        if self.candidate_bpw != 1.25 or self.control_bpw != 1.25:
            raise ValueError("Q16_EQUAL_RATE_DRIFT")
        if self.total_official_weights != 512 or self.tile_count != 8:
            raise ValueError("Q16_SCOPE_COUNT_DRIFT")


@dataclass(frozen=True)
class SourceGeneration:
    producer_head: str
    producer_run: int
    producer_job: int
    artifact_id: int
    artifact_zip_sha256: str
    receipt_digest: str
    source_admission_digest: str
    c2_request_digest: str
    official_repository: str
    official_revision: str
    index_sha256: str
    index_size_bytes: int
    header_sha256: str
    header_prefix_bytes: int
    total_source_evidence_bytes: int
    source_header_trial_eligible: bool
    source_bound_c2_request_admissible: bool
    blocker: str
    legacy_q7_disposition_digest: str | None = None

    def validate(self) -> None:
        expected = (S1_HEAD, S1_RUN, S1_JOB, S1_ARTIFACT_ID)
        if (self.producer_head, self.producer_run, self.producer_job, self.artifact_id) != expected:
            raise ValueError("S1_GENERATION_IDENTITY_MISMATCH")
        for name, got, expected_digest in (
            ("S1_ARTIFACT", self.artifact_zip_sha256, S1_ARTIFACT_ZIP_SHA256),
            ("S1_RECEIPT", self.receipt_digest, S1_RECEIPT),
            ("S1_SOURCE_ADMISSION", self.source_admission_digest, S1_SOURCE_ADMISSION_DIGEST),
            ("S1_C2_REQUEST", self.c2_request_digest, S1_C2_REQUEST_DIGEST),
            ("S1_INDEX", self.index_sha256, S1_INDEX_SHA256),
            ("S1_HEADER", self.header_sha256, S1_HEADER_SHA256),
        ):
            _require_sha(name, got)
            if got != expected_digest:
                raise ValueError(f"{name}_MISMATCH")
        if (self.official_repository, self.official_revision) != (OFFICIAL_REPOSITORY, OFFICIAL_REVISION):
            raise ValueError("S1_OFFICIAL_SOURCE_MISMATCH")
        if self.index_size_bytes != 11_359_251 or self.header_prefix_bytes != 105_432:
            raise ValueError("S1_BOUNDED_METADATA_SIZE_DRIFT")
        if self.total_source_evidence_bytes != 11_464_683:
            raise ValueError("S1_TOTAL_SOURCE_EVIDENCE_DRIFT")
        if not self.source_header_trial_eligible or not self.source_bound_c2_request_admissible:
            raise ValueError("S1_CURRENT_SOURCE_GATE_NOT_GREEN")
        if self.blocker != "NONE_HEADER_LEVEL_REQUEST_ADMISSIBLE":
            raise ValueError("S1_BLOCKER_STATE_DRIFT")
        if self.legacy_q7_disposition_digest is not None:
            raise ValueError("LEGACY_Q7_DISPOSITION_LAUNDERING")


def admit_current_generation_bounded_c2_proposal(
    representative: RepresentativeGeneration,
    source: SourceGeneration,
) -> dict[str, object]:
    representative.validate()
    source.validate()
    if (representative.official_repository, representative.official_revision) != (
        source.official_repository,
        source.official_revision,
    ):
        raise ValueError("CROSS_GENERATION_OFFICIAL_SOURCE_MISMATCH")

    body: dict[str, object] = {
        "schema": SCHEMA,
        "exact_other_agent_heads": [Q16_HEAD, S1_HEAD],
        "exact_other_agent_runs": [Q16_RUN, S1_RUN],
        "exact_other_agent_jobs": [Q16_JOB, S1_JOB],
        "exact_other_agent_artifacts": [Q16_ARTIFACT_ID, S1_ARTIFACT_ID],
        "official_repository": OFFICIAL_REPOSITORY,
        "official_revision": OFFICIAL_REVISION,
        "source_set_digest": SOURCE_SET_DIGEST,
        "q16_receipt_digest": representative.receipt_digest,
        "s1_receipt_digest": source.receipt_digest,
        "s1_source_admission_digest": source.source_admission_digest,
        "s1_c2_request_digest": source.c2_request_digest,
        "legacy_router_policy_head": PR674_POLICY_HEAD,
        "legacy_router_policy_blob": PR674_POLICY_BLOB,
        "legacy_q7_head": LEGACY_Q7_HEAD,
        "legacy_q7_disposition_digest": LEGACY_Q7_DISPOSITION_DIGEST,
        "legacy_q7_disposition_reused": False,
        "current_representative_generation_bound": True,
        "current_source_generation_bound": True,
        "representative_scope_complete": True,
        "representative_outcome": "E8_WIN",
        "source_header_trial_eligible": True,
        "source_bound_c2_request_admissible": True,
        "disposition": ELIGIBLE,
        "bounded_c2_request_proposal_eligible": True,
        "reason": "CURRENT_REPRESENTATIVE_E8_SCOPE_COMPLETE_AND_CURRENT_SOURCE_HEADER_C2_GATE_GREEN",
        "tensor_payload_bound": False,
        "real_tensor_quantization_observed": False,
        "model_execution_observed": False,
        "execution_authorized": False,
        "owner_host_execution_observed": False,
        "physical_io_performance_proven": False,
        "full_tensor_superiority_proven": False,
        "whole_model_superiority_proven": False,
        "quality_superiority_proven": False,
        "runtime_superiority_proven": False,
        "g2_admitted": False,
        "gate10_promoted": False,
        "semantic_k27_authority_minted": False,
        "native_private_transformer_kv_accessed": False,
        "laws": [
            "FreshGreenState!=LegacyPinnedDisposition",
            "CurrentGenerationIdentityBeforePolicyReuse",
            "RepresentativeScopeComplete+CurrentSourceGateGreen=>BoundedProposalOnly",
            "BoundedC2Proposal!=ExecutionAuthority",
            "SourceHeaderEligible!=TensorPayloadBound",
            "RepresentativeE8Win!=GeneralizedE8Superiority",
            "K27Coordinate!=SourceAuthority!=EffectAuthority",
        ],
    }
    body["receipt_digest"] = _sha(body)
    return body


def current_q16_fixture() -> RepresentativeGeneration:
    return RepresentativeGeneration(
        producer_head=Q16_HEAD, producer_run=Q16_RUN, producer_job=Q16_JOB,
        artifact_id=Q16_ARTIFACT_ID, artifact_zip_sha256=Q16_ARTIFACT_ZIP_SHA256,
        receipt_digest=Q16_RECEIPT, scope_admission_receipt=Q16_SCOPE_ADMISSION_RECEIPT,
        q5_receipt_digest=Q5_RECEIPT, official_repository=OFFICIAL_REPOSITORY,
        official_revision=OFFICIAL_REVISION, source_set_digest=SOURCE_SET_DIGEST,
        representative_scope_complete=True, minimum_missing_evidence_cone=(),
        aggregate_outcome="E8_WIN", aggregate_e8_over_control=0.6220981458103897,
        candidate_bpw=1.25, control_bpw=1.25, total_official_weights=512, tile_count=8,
    )


def current_s1_fixture() -> SourceGeneration:
    return SourceGeneration(
        producer_head=S1_HEAD, producer_run=S1_RUN, producer_job=S1_JOB,
        artifact_id=S1_ARTIFACT_ID, artifact_zip_sha256=S1_ARTIFACT_ZIP_SHA256,
        receipt_digest=S1_RECEIPT, source_admission_digest=S1_SOURCE_ADMISSION_DIGEST,
        c2_request_digest=S1_C2_REQUEST_DIGEST, official_repository=OFFICIAL_REPOSITORY,
        official_revision=OFFICIAL_REVISION, index_sha256=S1_INDEX_SHA256,
        index_size_bytes=11_359_251, header_sha256=S1_HEADER_SHA256,
        header_prefix_bytes=105_432, total_source_evidence_bytes=11_464_683,
        source_header_trial_eligible=True, source_bound_c2_request_admissible=True,
        blocker="NONE_HEADER_LEVEL_REQUEST_ADMISSIBLE",
    )


def main() -> None:
    print(json.dumps(admit_current_generation_bounded_c2_proposal(current_q16_fixture(), current_s1_fixture()), sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
