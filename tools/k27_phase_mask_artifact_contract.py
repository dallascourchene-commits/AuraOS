"""Content-bound K27 phase-mask materialization contract.

A K27 coordinate, storage offset, or storage-plan digest is only a lookup/
planning surface. Exact optical payload reuse requires artifact identity,
source/model generation, payload digest, and materialization generation to
agree at retrieval time.

This module performs no physical I/O and authorizes no optical effect.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Mapping, Sequence


SCHEMA = "AURA_K27_PHASE_MASK_ARTIFACT_RECEIPT_V1"
K27_SCHEME = "K27-B3MOD27-XYZ-v1"


def _hex_digest(name: str, value: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"{name} must be a 64-character SHA-256 hex digest")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError(f"{name} must be hexadecimal") from exc
    return value.lower()


def _positive_int(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _nonnegative_int(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


@dataclass(frozen=True)
class PhaseMaskArtifactIdentity:
    scene_source_sha256: str
    optical_model_generation: str
    phase_encoding_generation: str
    wavelength_nm: int
    width_px: int
    height_px: int
    dtype: str
    payload_sha256: str
    payload_bytes: int

    def validate(self) -> None:
        _hex_digest("scene_source_sha256", self.scene_source_sha256)
        _hex_digest("payload_sha256", self.payload_sha256)
        if not self.optical_model_generation:
            raise ValueError("optical_model_generation must be non-empty")
        if not self.phase_encoding_generation:
            raise ValueError("phase_encoding_generation must be non-empty")
        _positive_int("wavelength_nm", self.wavelength_nm)
        _positive_int("width_px", self.width_px)
        _positive_int("height_px", self.height_px)
        _positive_int("payload_bytes", self.payload_bytes)
        if not self.dtype:
            raise ValueError("dtype must be non-empty")

    def identity_digest(self) -> str:
        self.validate()
        return hashlib.sha256(_canonical_json(asdict(self)).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PlannedMaterialization:
    storage_object_id: str
    storage_generation: str
    storage_plan_digest: str
    planned_backend: str
    byte_offset: int
    aligned_extent_bytes: int

    def validate(self) -> None:
        if not self.storage_object_id:
            raise ValueError("storage_object_id must be non-empty")
        if not self.storage_generation:
            raise ValueError("storage_generation must be non-empty")
        _hex_digest("storage_plan_digest", self.storage_plan_digest)
        if self.planned_backend not in {"RAM", "MMAP_DEMAND", "NVME_PREFETCH", "DIRECT_SYNC"}:
            raise ValueError("planned_backend is unsupported")
        _nonnegative_int("byte_offset", self.byte_offset)
        _positive_int("aligned_extent_bytes", self.aligned_extent_bytes)

    def plan_binding_digest(self) -> str:
        self.validate()
        return hashlib.sha256(_canonical_json(asdict(self)).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class K27PhaseMaskHandle:
    k27_coordinate: int
    artifact_identity_digest: str
    plan_binding_digest: str

    def validate(self) -> None:
        if isinstance(self.k27_coordinate, bool) or not isinstance(self.k27_coordinate, int):
            raise ValueError("k27_coordinate must be an integer")
        if not 0 <= self.k27_coordinate <= 26:
            raise ValueError("k27_coordinate must be in [0,26]")
        _hex_digest("artifact_identity_digest", self.artifact_identity_digest)
        _hex_digest("plan_binding_digest", self.plan_binding_digest)


@dataclass(frozen=True)
class RetrievalObservation:
    storage_object_id: str
    storage_generation: str
    observed_byte_offset: int
    observed_payload_sha256: str
    observed_payload_bytes: int

    def validate(self) -> None:
        if not self.storage_object_id or not self.storage_generation:
            raise ValueError("observed storage identity must be non-empty")
        _nonnegative_int("observed_byte_offset", self.observed_byte_offset)
        _hex_digest("observed_payload_sha256", self.observed_payload_sha256)
        _positive_int("observed_payload_bytes", self.observed_payload_bytes)


@dataclass(frozen=True)
class RetrievalGate:
    artifact_exact: bool
    materialization_generation_exact: bool
    offset_exact: bool
    payload_exact: bool
    admissible_for_semantic_reuse: bool
    planned_backend_observed: bool = False
    physical_io_attested: bool = False
    optical_effect_authority: bool = False


def make_handle(
    *,
    k27_coordinate: int,
    artifact: PhaseMaskArtifactIdentity,
    plan: PlannedMaterialization,
) -> K27PhaseMaskHandle:
    artifact.validate()
    plan.validate()
    handle = K27PhaseMaskHandle(
        k27_coordinate=k27_coordinate,
        artifact_identity_digest=artifact.identity_digest(),
        plan_binding_digest=plan.plan_binding_digest(),
    )
    handle.validate()
    return handle


def validate_retrieval(
    *,
    handle: K27PhaseMaskHandle,
    artifact: PhaseMaskArtifactIdentity,
    plan: PlannedMaterialization,
    observation: RetrievalObservation,
) -> RetrievalGate:
    """Validate exact semantic artifact reuse without inferring physical I/O."""
    handle.validate()
    artifact.validate()
    plan.validate()
    observation.validate()

    artifact_exact = handle.artifact_identity_digest == artifact.identity_digest()
    plan_exact = handle.plan_binding_digest == plan.plan_binding_digest()
    generation_exact = (
        plan_exact
        and observation.storage_object_id == plan.storage_object_id
        and observation.storage_generation == plan.storage_generation
    )
    offset_exact = generation_exact and observation.observed_byte_offset == plan.byte_offset
    payload_exact = (
        observation.observed_payload_sha256 == artifact.payload_sha256
        and observation.observed_payload_bytes == artifact.payload_bytes
    )

    return RetrievalGate(
        artifact_exact=artifact_exact,
        materialization_generation_exact=generation_exact,
        offset_exact=offset_exact,
        payload_exact=payload_exact,
        admissible_for_semantic_reuse=artifact_exact and generation_exact and offset_exact and payload_exact,
    )


def build_phase_mask_receipt(
    *,
    handle: K27PhaseMaskHandle,
    artifact: PhaseMaskArtifactIdentity,
    plan: PlannedMaterialization,
    gate: RetrievalGate,
    parent_artifact_ids: Sequence[str],
) -> Mapping[str, object]:
    parents = tuple(parent_artifact_ids)
    if len(parents) != 2 or len(set(parents)) != 2 or any(not p for p in parents):
        raise ValueError("exactly two distinct non-empty parent artifact IDs are required")
    handle.validate()
    artifact.validate()
    plan.validate()

    payload = {
        "schema": SCHEMA,
        "k27_scheme": K27_SCHEME,
        "parent_artifact_ids": parents,
        "handle": asdict(handle),
        "artifact": asdict(artifact),
        "plan": asdict(plan),
        "retrieval_gate": asdict(gate),
        "claim_ceiling": {
            "k27_coordinate_is_artifact_identity": False,
            "storage_offset_is_artifact_identity": False,
            "storage_plan_was_executed": False,
            "planned_backend_was_observed": False,
            "physical_io_attested": False,
            "phase_mask_optically_correct": False,
            "display_effect_authorized": False,
            "native_transformer_kv_accessed": False,
            "gate10_promoted": False,
        },
    }
    digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    return {**payload, "receipt_sha256": digest}


def verify_phase_mask_receipt(receipt: Mapping[str, object]) -> bool:
    expected = {
        "schema",
        "k27_scheme",
        "parent_artifact_ids",
        "handle",
        "artifact",
        "plan",
        "retrieval_gate",
        "claim_ceiling",
        "receipt_sha256",
    }
    if set(receipt) != expected:
        return False
    if receipt.get("schema") != SCHEMA or receipt.get("k27_scheme") != K27_SCHEME:
        return False
    ceiling = receipt.get("claim_ceiling")
    if not isinstance(ceiling, dict) or not ceiling or any(v is not False for v in ceiling.values()):
        return False
    payload = {key: receipt[key] for key in expected if key != "receipt_sha256"}
    expected_digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    return receipt.get("receipt_sha256") == expected_digest
