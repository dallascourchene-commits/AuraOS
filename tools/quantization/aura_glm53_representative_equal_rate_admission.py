#!/usr/bin/env python3
"""Q16: bind the exact official equal-rate Q5 canary into the Q6 scope membrane.

This child creates no quantizer and no wider quality claim.  Q5 owns the measured
E8-vs-control distortion evidence; Q6 owns representative-scope admission.  Q16
only validates the exact Q5 receipt and translates its eight registered tiles
into Q6 observations.
"""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any

from tools.quantization import aura_representative_canary_evidence_admission as scope_owner

SCHEMA = "AURA_GLM53_REPRESENTATIVE_EQUAL_RATE_ADMISSION_V1"

Q5_HEAD = "eb5887a1f2a26d763dd312b1c84af9ea7f961fe3"
Q5_RUN = 33401474768
Q5_JOB = 99518559654
Q5_WORKFLOW = "GLM53 Official Equal Rate E8 Canary"
Q5_SOURCE_BLOB = "5b39ce1132f8ef520529487411628be04e51f32a"
Q5_RECEIPT_DIGEST = "00bae035570665f19c40405c8d04002f894f6a7c05c75155ce9e63d8dcf9f01a"
Q5_AGGREGATE_E8_OVER_CONTROL = 0.6220981458103897

Q6_HEAD = "6906337dd6e75f49a70a84652bfd9ab70d967eef"
Q6_RUN = 33401482324
Q6_JOB = 99518584784
Q6_WORKFLOW = "Aura Representative Canary Evidence Admission"
Q6_SOURCE_BLOB = "400a28e12b2c8ac37b59c36ef7386bcb443b1923"

SOURCE_SET_DIGEST = "f41495beb566f4c49f5674f2820f3d5c32591647be552048cf711a885a1b71b6"
EXACT_BPW = 1.25
EXPECTED_TILE_IDS = tuple(
    f"{role}:{col}"
    for role in ("gate_up_proj", "down_proj")
    for col in (0, 128, 256, 384)
)


class RepresentativeEqualRateAdmissionError(ValueError):
    pass


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def _sha(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _receipt_body(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key != "receipt_digest"}


def validate_exact_q5_receipt(payload: dict[str, Any]) -> None:
    if payload.get("receipt_digest") != Q5_RECEIPT_DIGEST:
        raise RepresentativeEqualRateAdmissionError("Q5_RECEIPT_DIGEST_MISMATCH")
    if _sha(_receipt_body(payload)) != Q5_RECEIPT_DIGEST:
        raise RepresentativeEqualRateAdmissionError("Q5_RECEIPT_BODY_DIGEST_MISMATCH")
    if payload.get("schema") != "AURA_GLM53_OFFICIAL_EQUAL_RATE_E8_CANARY_V1":
        raise RepresentativeEqualRateAdmissionError("Q5_SCHEMA_MISMATCH")
    if payload.get("q13_source_tensor_set_digest") != SOURCE_SET_DIGEST:
        raise RepresentativeEqualRateAdmissionError("Q5_SOURCE_SET_MISMATCH")
    if payload.get("codec_bpw_e8") != EXACT_BPW or payload.get("codec_bpw_control") != EXACT_BPW:
        raise RepresentativeEqualRateAdmissionError("Q5_RATE_MISMATCH")
    if payload.get("equal_rate") is not True:
        raise RepresentativeEqualRateAdmissionError("Q5_EQUAL_RATE_NOT_PROVEN")
    if payload.get("total_official_weights_observed") != 512:
        raise RepresentativeEqualRateAdmissionError("Q5_WEIGHT_COUNT_MISMATCH")
    if payload.get("aggregate_outcome") != "E8_WIN":
        raise RepresentativeEqualRateAdmissionError("Q5_AGGREGATE_OUTCOME_DRIFT")
    ratio = float(payload.get("aggregate_e8_over_control", math.nan))
    if not math.isclose(ratio, Q5_AGGREGATE_E8_OVER_CONTROL, rel_tol=0.0, abs_tol=1e-15):
        raise RepresentativeEqualRateAdmissionError("Q5_AGGREGATE_RATIO_DRIFT")
    if payload.get("official_source_equal_rate_distortion_evidence") is not True:
        raise RepresentativeEqualRateAdmissionError("Q5_OFFICIAL_EVIDENCE_NOT_BOUND")
    if payload.get("representative_canary_scope_only") is not True:
        raise RepresentativeEqualRateAdmissionError("Q5_SCOPE_CEILING_DRIFT")
    for key in (
        "geometry_privileged",
        "full_tensor_quantized",
        "whole_model_quantized",
        "glm_quality_proven",
        "runtime_performance_proven",
        "native_private_transformer_kv_accessed",
        "semantic_k27_authority",
        "gate10_promoted",
    ):
        if payload.get(key) is not False:
            raise RepresentativeEqualRateAdmissionError(f"Q5_PROMOTION_CEILING_DRIFT:{key}")

    tiles = payload.get("tiles")
    if not isinstance(tiles, list) or len(tiles) != 8:
        raise RepresentativeEqualRateAdmissionError("Q5_TILE_COUNT_MISMATCH")
    ids = [f"{row.get('tensor_role')}:{row.get('col_start')}" for row in tiles]
    if set(ids) != set(EXPECTED_TILE_IDS) or len(set(ids)) != 8:
        raise RepresentativeEqualRateAdmissionError("Q5_TILE_REGISTRY_MISMATCH")


def _translate_tiles(payload: dict[str, Any]) -> tuple[scope_owner.CanaryObservation, ...]:
    observations: list[scope_owner.CanaryObservation] = []
    for row in payload["tiles"]:
        observations.append(
            scope_owner.CanaryObservation(
                tile_id=f"{row['tensor_role']}:{row['col_start']}",
                source_set_digest=SOURCE_SET_DIGEST,
                source_tile_sha256=str(row["canonical_float32_tile_sha256"]),
                candidate_payload_sha256=str(row["e8_payload_sha256"]),
                control_payload_sha256=str(row["control_payload_sha256"]),
                bits_per_weight=EXACT_BPW,
                candidate_mse=float(row["e8_mse"]),
                control_mse=float(row["control_mse"]),
                outcome=str(row["outcome"]),
            )
        )
    return tuple(observations)


def admit_exact_q5_representative_evidence(payload: dict[str, Any]) -> dict[str, Any]:
    validate_exact_q5_receipt(payload)
    scope = scope_owner.RegisteredCanaryScope(
        scope_id="GLM53_LAYER3_EXPERT0_Q5_EQUAL_RATE_8_TILE_V1",
        source_set_digest=SOURCE_SET_DIGEST,
        expected_tile_ids=EXPECTED_TILE_IDS,
        exact_bits_per_weight=EXACT_BPW,
        metric="MSE",
    )
    admitted = scope_owner.admit_representative_canary_evidence(scope, _translate_tiles(payload))
    if admitted["registered_scope_complete"] is not True:
        raise RepresentativeEqualRateAdmissionError("REPRESENTATIVE_SCOPE_NOT_COMPLETE")
    if admitted["missing_tile_ids"] != []:
        raise RepresentativeEqualRateAdmissionError("REPRESENTATIVE_SCOPE_HAS_MISSING_TILES")
    if admitted["outcome_counts"] != {"CONTROL_WIN": 0, "E8_WIN": 8, "TIE": 0}:
        raise RepresentativeEqualRateAdmissionError("REPRESENTATIVE_OUTCOME_COUNT_DRIFT")
    if admitted["next_work_mode"] != "STOP_OR_REGISTER_HIGHER_SCOPE":
        raise RepresentativeEqualRateAdmissionError("REPRESENTATIVE_NEXT_WORK_DRIFT")

    body: dict[str, Any] = {
        "schema": SCHEMA,
        "q5_head": Q5_HEAD,
        "q5_run": Q5_RUN,
        "q5_job": Q5_JOB,
        "q5_workflow": Q5_WORKFLOW,
        "q5_source_blob": Q5_SOURCE_BLOB,
        "q5_receipt_digest": Q5_RECEIPT_DIGEST,
        "q6_head": Q6_HEAD,
        "q6_run": Q6_RUN,
        "q6_job": Q6_JOB,
        "q6_workflow": Q6_WORKFLOW,
        "q6_source_blob": Q6_SOURCE_BLOB,
        "source_set_digest": SOURCE_SET_DIGEST,
        "exact_bits_per_weight": EXACT_BPW,
        "official_weights_observed": 512,
        "registered_tile_count": 8,
        "outcome_counts": admitted["outcome_counts"],
        "aggregate_e8_over_control": float(payload["aggregate_e8_over_control"]),
        "aggregate_outcome": payload["aggregate_outcome"],
        "representative_scope_complete": admitted["registered_scope_complete"],
        "minimum_missing_evidence_cone": admitted["minimum_missing_evidence_cone"],
        "next_work_mode": admitted["next_work_mode"],
        "scope_admission_receipt_digest": admitted["receipt_digest"],
        "representative_evidence_only": True,
        "geometry_superiority_proven": False,
        "full_tensor_superiority_proven": False,
        "full_model_superiority_proven": False,
        "quality_superiority_proven": False,
        "runtime_superiority_proven": False,
        "model_execution_observed": False,
        "effect_authority": False,
        "native_private_transformer_kv_accessed": False,
        "semantic_k27_authority": False,
        "gate10_promoted": False,
        "merge_or_deployment_authorized": False,
        "laws": (
            "EightOfEightEqualRateCanaryWins!=GlobalGeometrySuperiority",
            "RepresentativeScopeComplete=>StopOrRegisterHigherScope",
            "ExactQ5Receipt+ExactQ6ScopeOwner=>ScopedRepresentativeEvidence",
            "DistortionEvidence!=ModelQuality!=RuntimePerformance",
            "K27Coordinate!=SemanticAuthority",
        ),
    }
    body["receipt_digest"] = _sha(body)
    return body


__all__ = [
    "EXPECTED_TILE_IDS",
    "RepresentativeEqualRateAdmissionError",
    "admit_exact_q5_representative_evidence",
    "validate_exact_q5_receipt",
]
