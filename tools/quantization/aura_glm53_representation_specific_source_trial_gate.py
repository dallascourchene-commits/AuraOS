#!/usr/bin/env python3
"""Join exact official-source admission with exact quantization representation identity.

The public Q7 boundary is deliberately zero-input.  It regenerates Q5's current
AdmissionState through the exact materialized Q5 producer and regenerates Q6's
canonical target representation.  Caller-authored source snapshots, booleans,
digests, target identities, or JSON files cannot mint a header-level candidate.

A private helper accepts typed producer states only for adversarial tests of
future evidence transitions.  It is not an admission API.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json

from tools.quantization.aura_glm53_official_source_admission import (
    AdmissionState,
    OFFICIAL_COMMIT,
    OFFICIAL_REPO,
    PR628_E8_PAGE_ARTIFACT_SHA,
    PR628_E8_PAGE_SCHEME,
    current_public_state,
)
from tools.quantization.aura_glm53_quantization_evidence_transfer import (
    QuantizationRepresentationIdentity,
    q5_representation_identity,
)

VERSION = "AURA_GLM53_REPRESENTATION_SPECIFIC_SOURCE_TRIAL_GATE_V2"
Q6_EXACT_HEAD = "4137aabd972feff9c4412bb4786ef8fd4de207e0"
Q6_EXACT_RUN = 33370305329
Q5_SOURCE_EXACT_HEAD = "730426b82235b0ff4e75fef1cff00707877a84ad"
Q5_SOURCE_EXACT_RUN = 33369967425
Q5_SOURCE_BLOB_SHA = "7ed09c57699fe303f555a3b6bdaadb791c64223f"
Q5_SOURCE_SCHEMA = "AURA_GLM53_OFFICIAL_QUANTIZATION_SOURCE_ADMISSION_V1"
OFFICIAL_REPOSITORY = OFFICIAL_REPO
OFFICIAL_REVISION = OFFICIAL_COMMIT
PR628_EXACT_CANDIDATE = PR628_E8_PAGE_ARTIFACT_SHA
PR628_SCHEME = PR628_E8_PAGE_SCHEME

__all__ = (
    "RepresentationSpecificSourceTrialReceipt",
    "current_representation_specific_source_trial",
)


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _sha(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _validate_source_admission(source: AdmissionState) -> dict[str, object]:
    if type(source) is not AdmissionState:
        raise ValueError("Q5_ADMISSION_STATE_TYPE_REQUIRED")
    out = asdict(source)
    if out["schema"] != Q5_SOURCE_SCHEMA:
        raise ValueError("SOURCE_SCHEMA_ID_MISMATCH")
    if out["official_repository"] != OFFICIAL_REPOSITORY or out["official_revision"] != OFFICIAL_REVISION:
        raise ValueError("OFFICIAL_SOURCE_GENERATION_MISMATCH")
    if out["candidate_parent_sha"] != PR628_EXACT_CANDIDATE or out["candidate_scheme"] != PR628_SCHEME:
        raise ValueError("SOURCE_CANDIDATE_REPRESENTATION_MISMATCH")
    if out["semantic_k27_authority"] or out["native_transformer_kv_accessed"] or out["gate10_promoted"]:
        raise ValueError("Q5_PARENT_CEILING_WIDENED")
    if not out["config_profile_bound"] or not out["index_object_identity_bound"] or not out["candidate_representation_bound"]:
        raise ValueError("Q5_BASELINE_BINDINGS_REQUIRED")
    if not out["index_bytes_verified"]:
        forbidden = (
            out["representative_key_to_shard_bound"],
            out["representative_headers_observed"],
            out["fp8_companions_bound"],
            out["header_trial_eligible"],
            out["source_tensor_payload_bound"],
            out["real_tensor_quantization_eligible"],
        )
        if any(forbidden):
            raise ValueError("Q5_SOURCE_EVIDENCE_ORDER_VIOLATION")
    if out["header_trial_eligible"] and not (
        out["index_bytes_verified"]
        and out["representative_key_to_shard_bound"]
        and out["representative_headers_observed"]
        and out["fp8_companions_bound"]
    ):
        raise ValueError("HEADER_ELIGIBLE_WITH_INCOMPLETE_Q5_EVIDENCE")
    if out["real_tensor_quantization_eligible"] and not (
        out["header_trial_eligible"] and out["source_tensor_payload_bound"]
    ):
        raise ValueError("REAL_QUANTIZATION_WITHOUT_PAYLOAD")
    return out


@dataclass(frozen=True)
class RepresentationSpecificSourceTrialReceipt:
    version: str
    exact_parent_heads: tuple[str, str]
    exact_parent_runs: tuple[int, int]
    q5_source_blob_sha: str
    source_producer_traversed: bool
    source_snapshot_caller_supplied: bool
    source_admission_digest: str
    target_representation_digest: str
    target_scheme: str
    source_candidate_scheme: str
    source_candidate_parent_sha: str
    source_header_eligible: bool
    exact_target_representation_identity_bound: bool
    disposition: str
    header_bound_representation_trial_candidate: bool
    source_tensor_payload_bound: bool
    real_tensor_quantization_eligible: bool
    evidence_transfer_authorized: bool
    glm53_quality_evidence: bool
    runtime_evidence: bool
    semantic_k27_authority: bool
    native_private_transformer_kv_accessed: bool
    gate10_promoted: bool
    deployment_authorized: bool

    @property
    def receipt_digest(self) -> str:
        return _sha(asdict(self))


def _classify_producer_state_for_test(
    source: AdmissionState,
    target: QuantizationRepresentationIdentity,
) -> RepresentationSpecificSourceTrialReceipt:
    """Internal adversarial transition helper; not a public admission boundary."""
    source_dict = _validate_source_admission(source)
    if type(target) is not QuantizationRepresentationIdentity:
        raise ValueError("Q6_REPRESENTATION_IDENTITY_TYPE_REQUIRED")
    target.validate()
    canonical_target = q5_representation_identity()
    exact_target = target.identity_digest == canonical_target.identity_digest
    header_ready = bool(source_dict["header_trial_eligible"])

    if not header_ready:
        disposition = "HOLD_SOURCE_HEADER_NOT_ELIGIBLE"
        candidate = False
    else:
        if source_dict["source_tensor_payload_bound"] or source_dict["real_tensor_quantization_eligible"]:
            raise ValueError("Q7_HEADER_GATE_CANNOT_CONSUME_PAYLOAD_OR_EXECUTION_PROMOTION")
        if not exact_target:
            disposition = "HOLD_REPRESENTATION_IDENTITY_MISMATCH"
            candidate = False
        else:
            disposition = "HEADER_BOUND_REPRESENTATION_TRIAL_CANDIDATE"
            candidate = True

    return RepresentationSpecificSourceTrialReceipt(
        version=VERSION,
        exact_parent_heads=(Q6_EXACT_HEAD, Q5_SOURCE_EXACT_HEAD),
        exact_parent_runs=(Q6_EXACT_RUN, Q5_SOURCE_EXACT_RUN),
        q5_source_blob_sha=Q5_SOURCE_BLOB_SHA,
        source_producer_traversed=True,
        source_snapshot_caller_supplied=False,
        source_admission_digest=source.digest(),
        target_representation_digest=target.identity_digest,
        target_scheme=target.scheme,
        source_candidate_scheme=str(source_dict["candidate_scheme"]),
        source_candidate_parent_sha=str(source_dict["candidate_parent_sha"]),
        source_header_eligible=header_ready,
        exact_target_representation_identity_bound=exact_target,
        disposition=disposition,
        header_bound_representation_trial_candidate=candidate,
        source_tensor_payload_bound=bool(source_dict["source_tensor_payload_bound"]),
        real_tensor_quantization_eligible=False,
        evidence_transfer_authorized=False,
        glm53_quality_evidence=False,
        runtime_evidence=False,
        semantic_k27_authority=False,
        native_private_transformer_kv_accessed=False,
        gate10_promoted=False,
        deployment_authorized=False,
    )


def current_representation_specific_source_trial() -> RepresentationSpecificSourceTrialReceipt:
    """Regenerate both exact parent-owned planes and return the current Q7 state."""
    return _classify_producer_state_for_test(
        current_public_state(),
        q5_representation_identity(),
    )


def main() -> None:
    receipt = current_representation_specific_source_trial()
    print(json.dumps({**asdict(receipt), "receipt_digest": receipt.receipt_digest}, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
