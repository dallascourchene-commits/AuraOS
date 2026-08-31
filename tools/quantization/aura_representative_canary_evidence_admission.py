#!/usr/bin/env python3
"""Fail-closed admission for bounded representative quantization canaries.

The membrane deliberately separates three questions:
1. Is each reported tile bound to the registered representative source scope?
2. Has the registered representative scope been completely observed at an exact rate?
3. Does the representative evidence authorize a wider geometry/model claim? (V1: never.)

It is evidence accounting only. It performs no quantization, model execution, provider
call, promotion, or authority transition.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
import re
from typing import Iterable

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ALLOWED_OUTCOMES = {"E8_WIN", "CONTROL_WIN", "TIE"}
SCHEMA = "AURA_REPRESENTATIVE_CANARY_EVIDENCE_ADMISSION_V1"


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _require_sha256(name: str, value: str) -> None:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise ValueError(f"{name} must be lowercase SHA-256")


@dataclass(frozen=True)
class RegisteredCanaryScope:
    scope_id: str
    source_set_digest: str
    expected_tile_ids: tuple[str, ...]
    exact_bits_per_weight: float
    metric: str = "MSE"

    def validate(self) -> None:
        if not self.scope_id:
            raise ValueError("scope_id required")
        _require_sha256("source_set_digest", self.source_set_digest)
        if self.metric != "MSE":
            raise ValueError("V1 admits only MSE")
        if not math.isfinite(self.exact_bits_per_weight) or self.exact_bits_per_weight <= 0:
            raise ValueError("exact_bits_per_weight must be finite and positive")
        if not self.expected_tile_ids:
            raise ValueError("expected_tile_ids must be non-empty")
        if len(set(self.expected_tile_ids)) != len(self.expected_tile_ids):
            raise ValueError("expected_tile_ids must be unique")
        if any(not isinstance(tile_id, str) or not tile_id for tile_id in self.expected_tile_ids):
            raise ValueError("every expected tile id must be non-empty text")


@dataclass(frozen=True)
class CanaryObservation:
    tile_id: str
    source_set_digest: str
    source_tile_sha256: str
    candidate_payload_sha256: str
    control_payload_sha256: str
    bits_per_weight: float
    candidate_mse: float
    control_mse: float
    outcome: str

    def validate(self, scope: RegisteredCanaryScope) -> None:
        if self.tile_id not in scope.expected_tile_ids:
            raise ValueError("observation tile is outside registered scope")
        if self.source_set_digest != scope.source_set_digest:
            raise ValueError("observation source set does not match registered scope")
        _require_sha256("source_tile_sha256", self.source_tile_sha256)
        _require_sha256("candidate_payload_sha256", self.candidate_payload_sha256)
        _require_sha256("control_payload_sha256", self.control_payload_sha256)
        if self.bits_per_weight != scope.exact_bits_per_weight:
            raise ValueError("candidate/control observation rate drift")
        if not math.isfinite(self.candidate_mse) or self.candidate_mse < 0:
            raise ValueError("candidate_mse must be finite and non-negative")
        if not math.isfinite(self.control_mse) or self.control_mse < 0:
            raise ValueError("control_mse must be finite and non-negative")
        if self.outcome not in ALLOWED_OUTCOMES:
            raise ValueError("unrecognized canary outcome")
        derived = classify_outcome(self.candidate_mse, self.control_mse)
        if self.outcome != derived:
            raise ValueError("declared outcome disagrees with exact MSE ordering")


def classify_outcome(candidate_mse: float, control_mse: float) -> str:
    if candidate_mse < control_mse:
        return "E8_WIN"
    if candidate_mse > control_mse:
        return "CONTROL_WIN"
    return "TIE"


def admit_representative_canary_evidence(
    scope: RegisteredCanaryScope,
    observations: Iterable[CanaryObservation],
) -> dict[str, object]:
    """Return a deterministic evidence receipt and the exact remaining verification cone.

    Representative completion is intentionally not a geometry-wide promotion gate. Even
    unanimous results remain scoped evidence. A wider experiment must be separately
    registered and justified; V1 exposes no boolean that can widen this claim.
    """

    scope.validate()
    rows = list(observations)
    seen: set[str] = set()
    for row in rows:
        row.validate(scope)
        if row.tile_id in seen:
            raise ValueError("duplicate observation for registered tile")
        seen.add(row.tile_id)

    canonical_rows = sorted(rows, key=lambda row: row.tile_id)
    missing = sorted(set(scope.expected_tile_ids) - seen)
    counts = {outcome: 0 for outcome in sorted(ALLOWED_OUTCOMES)}
    for row in canonical_rows:
        counts[row.outcome] += 1

    complete = not missing
    if complete:
        disposition = "REPRESENTATIVE_SCOPE_COMPLETE"
        next_work_mode = "STOP_OR_REGISTER_HIGHER_SCOPE"
    else:
        disposition = "REPRESENTATIVE_VERIFICATION_INCOMPLETE"
        next_work_mode = "VERIFICATION"

    body: dict[str, object] = {
        "schema": SCHEMA,
        "scope": asdict(scope),
        "observations": [asdict(row) for row in canonical_rows],
        "observed_tile_ids": [row.tile_id for row in canonical_rows],
        "missing_tile_ids": missing,
        "minimum_missing_evidence_cone": missing,
        "outcome_counts": counts,
        "registered_scope_complete": complete,
        "disposition": disposition,
        "next_work_mode": next_work_mode,
        "support_merge_eligible": bool(canonical_rows),
        "semantic_sibling_credit": False,
        "representative_evidence_only": True,
        "geometry_superiority_proven": False,
        "full_tensor_superiority_proven": False,
        "full_model_superiority_proven": False,
        "quality_superiority_proven": False,
        "runtime_superiority_proven": False,
        "effect_authority": False,
        "gate10_promoted": False,
        "native_private_kv_accessed": False,
        "semantic_k27_authority": False,
        "laws": [
            "RepresentativeCanaryEvidence!=GeometryWideEvidence",
            "MatchedRate+SameTile!=FullTensorComparability",
            "UnanimousRepresentativeOutcome!=GlobalSuperiority",
            "VerificationCompletionMayIncreaseEGKWithoutMintingSCK",
            "MinimumMissingEvidenceConeBeforeFanout",
            "HigherScopeRequiresSeparateRegistration",
            "K27Coordinate!=SemanticAuthority",
        ],
    }
    body["receipt_digest"] = digest(body)
    return body


__all__ = [
    "RegisteredCanaryScope",
    "CanaryObservation",
    "admit_representative_canary_evidence",
    "classify_outcome",
    "digest",
]
