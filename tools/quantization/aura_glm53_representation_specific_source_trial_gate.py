#!/usr/bin/env python3
"""Join exact official-source admission with exact quantization representation identity.

Q7 does not verify official bytes (Q5 owns that) and does not define representation
identity/evidence transfer (Q6 owns that). It only decides whether those two exact
planes are jointly sufficient to request a bounded header-level source trial.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from tools.quantization.aura_glm53_quantization_evidence_transfer import (
    QuantizationRepresentationIdentity,
    q5_representation_identity,
)

VERSION = "AURA_GLM53_REPRESENTATION_SPECIFIC_SOURCE_TRIAL_GATE_V1"
Q6_EXACT_HEAD = "4137aabd972feff9c4412bb4786ef8fd4de207e0"
Q6_EXACT_RUN = 33370305329
Q5_SOURCE_EXACT_HEAD = "730426b82235b0ff4e75fef1cff00707877a84ad"
Q5_SOURCE_EXACT_RUN = 33369967425
Q5_SOURCE_SCHEMA = "AURA_GLM53_OFFICIAL_QUANTIZATION_SOURCE_ADMISSION_V1"
OFFICIAL_REPOSITORY = "zai-org/GLM-5.3"
OFFICIAL_REVISION = "7cda81930d6e4cef42f48555de830aa32ecdde28"
PR628_EXACT_CANDIDATE = "b8fd399ee0ca6b45a4ec7db58750e6d4105ae3ae"
PR628_SCHEME = "AURA_E8_BALL10_16BIT_REF_V1"

SOURCE_KEYS = (
    "schema",
    "official_repository",
    "official_revision",
    "candidate_parent_sha",
    "candidate_scheme",
    "config_profile_bound",
    "index_object_identity_bound",
    "index_bytes_verified",
    "representative_key_to_shard_bound",
    "representative_headers_observed",
    "fp8_companions_bound",
    "candidate_representation_bound",
    "header_trial_eligible",
    "source_tensor_payload_bound",
    "real_tensor_quantization_eligible",
    "blocker",
    "semantic_k27_authority",
    "native_transformer_kv_accessed",
    "gate10_promoted",
)


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def _sha(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _exact_bool(name: str, value: object) -> bool:
    if type(value) is not bool:
        raise ValueError("BOOLEAN_REQUIRED:" + name)
    return value


def validate_source_admission(raw: Mapping[str, object]) -> dict[str, object]:
    if set(raw) != set(SOURCE_KEYS):
        missing = sorted(set(SOURCE_KEYS) - set(raw))
        extra = sorted(set(raw) - set(SOURCE_KEYS))
        raise ValueError(f"SOURCE_SCHEMA_MISMATCH:missing={missing}:extra={extra}")
    out = dict(raw)
    if out["schema"] != Q5_SOURCE_SCHEMA:
        raise ValueError("SOURCE_SCHEMA_ID_MISMATCH")
    if out["official_repository"] != OFFICIAL_REPOSITORY or out["official_revision"] != OFFICIAL_REVISION:
        raise ValueError("OFFICIAL_SOURCE_GENERATION_MISMATCH")
    if out["candidate_parent_sha"] != PR628_EXACT_CANDIDATE or out["candidate_scheme"] != PR628_SCHEME:
        raise ValueError("SOURCE_CANDIDATE_REPRESENTATION_MISMATCH")
    for key in SOURCE_KEYS:
        if key.endswith("_bound") or key.endswith("_eligible") or key in {
            "config_profile_bound",
            "index_object_identity_bound",
            "candidate_representation_bound",
            "semantic_k27_authority",
            "native_transformer_kv_accessed",
            "gate10_promoted",
        }:
            _exact_bool(key, out[key])
    if type(out["blocker"]) is not str:
        raise ValueError("BLOCKER_STRING_REQUIRED")
    if not out["config_profile_bound"] or not out["index_object_identity_bound"] or not out["candidate_representation_bound"]:
        raise ValueError("Q5_BASELINE_BINDINGS_REQUIRED")
    if out["semantic_k27_authority"] or out["native_transformer_kv_accessed"] or out["gate10_promoted"]:
        raise ValueError("Q5_PARENT_CEILING_WIDENED")
    if out["real_tensor_quantization_eligible"] and not out["source_tensor_payload_bound"]:
        raise ValueError("REAL_QUANTIZATION_WITHOUT_PAYLOAD")
    return out


@dataclass(frozen=True)
class RepresentationSpecificSourceTrialReceipt:
    version: str
    exact_parent_heads: tuple[str, str]
    exact_parent_runs: tuple[int, int]
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


def classify_source_trial(
    source_admission: Mapping[str, object],
    target_representation: QuantizationRepresentationIdentity | None = None,
) -> RepresentationSpecificSourceTrialReceipt:
    source = validate_source_admission(source_admission)
    target = target_representation or q5_representation_identity()
    target.validate()
    canonical_target = q5_representation_identity()
    exact_target = target.identity_digest == canonical_target.identity_digest
    header_ready = bool(source["header_trial_eligible"])

    if not header_ready:
        disposition = "HOLD_SOURCE_HEADER_NOT_ELIGIBLE"
        candidate = False
    else:
        required = (
            "index_bytes_verified",
            "representative_key_to_shard_bound",
            "representative_headers_observed",
            "fp8_companions_bound",
            "candidate_representation_bound",
        )
        if not all(bool(source[name]) for name in required):
            raise ValueError("HEADER_ELIGIBLE_WITH_INCOMPLETE_Q5_EVIDENCE")
        if source["source_tensor_payload_bound"] or source["real_tensor_quantization_eligible"]:
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
        source_admission_digest=_sha(source),
        target_representation_digest=target.identity_digest,
        target_scheme=target.scheme,
        source_candidate_scheme=str(source["candidate_scheme"]),
        source_candidate_parent_sha=str(source["candidate_parent_sha"]),
        source_header_eligible=header_ready,
        exact_target_representation_identity_bound=exact_target,
        disposition=disposition,
        header_bound_representation_trial_candidate=candidate,
        source_tensor_payload_bound=bool(source["source_tensor_payload_bound"]),
        real_tensor_quantization_eligible=False,
        evidence_transfer_authorized=False,
        glm53_quality_evidence=False,
        runtime_evidence=False,
        semantic_k27_authority=False,
        native_private_transformer_kv_accessed=False,
        gate10_promoted=False,
        deployment_authorized=False,
    )


def load_source(path: Path) -> dict[str, object]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("SOURCE_ADMISSION_OBJECT_REQUIRED")
    return raw


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-json", type=Path, required=True)
    args = parser.parse_args()
    receipt = classify_source_trial(load_source(args.source_json))
    print(json.dumps({**asdict(receipt), "receipt_digest": receipt.receipt_digest}, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
