"""Two-lane software-verification bundle for bounded Aura spatial-optics evidence.

V2 rebinds the independent-conformance lane to the repaired PR620 producer
semantics. A historical green receipt is not enough: every bundle construction
re-executes the current canonical PR620 conformance producer through its verifier.
The PR619 field-invariant lane remains independently scoped.

This bundle is software verification only, not physical validation.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import hashlib
import json
from typing import Mapping

from spatial.optical_invariant_witness import (
    OpticalInvariantReceiptV1,
    PROPAGATOR as INVARIANT_PROPAGATOR,
    SCHEMA as INVARIANT_SCHEMA,
)
import k27_optics_independent_conformance as conformance

SCHEMA = "AURA_SPATIAL_OPTICS_SOFTWARE_VERIFICATION_BUNDLE_V2"
CONFORMANCE_SEMANTIC_GENERATION = "PR620:5a5878eace5974ff6a3f1dbf676fed8295bb457a"
CONFORMANCE_OWNER_BLOB = "533c9e3926ff027367adef907b47bc01c74a6d4b"
INVARIANT_SEMANTIC_GENERATION = "PR619:c74239e79244b877d63f4952cea590ea6e122e78"
EXPECTED_IMPORTED_SOURCE_SHA256 = conformance.IMPORTED_SOURCE_SHA256
LANES = (
    "FIELD_INVARIANT_MEASUREMENT",
    "INDEPENDENT_FORMULATION_CONFORMANCE",
)
REOPEN_REQUIREMENTS = (
    "SHARED_IMPLEMENTATION_GENERATION",
    "EXACT_SHARED_FIXTURE_DIGEST",
    "EXACT_SHARED_SAMPLING_OR_GRID_DIGEST",
    "EXACT_SHARED_SOURCE_BINDING",
)


class VerificationBundleError(ValueError):
    pass


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _verify_invariant_receipt(receipt: OpticalInvariantReceiptV1) -> bool:
    if type(receipt) is not OpticalInvariantReceiptV1:
        return False
    if receipt.schema != INVARIANT_SCHEMA or receipt.propagator != INVARIANT_PROPAGATOR:
        return False
    if len(receipt.receipt_sha256) != 64:
        return False
    try:
        int(receipt.receipt_sha256, 16)
    except ValueError:
        return False
    unsigned = replace(receipt, receipt_sha256="")
    expected = hashlib.sha256(
        json.dumps(asdict(unsigned), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if receipt.receipt_sha256 != expected:
        return False
    if (
        receipt.phase_only_full_field_fidelity_proven
        or receipt.speckle_elimination_proven
        or receipt.rayleigh_sommerfeld_implementation_proven
        or receipt.physical_display_fidelity_proven
        or receipt.semantic_k27_authority
        or receipt.native_transformer_kv_accessed
    ):
        return False
    return True


def _require_closed_invariant_lane(receipt: OpticalInvariantReceiptV1) -> None:
    if not _verify_invariant_receipt(receipt):
        raise VerificationBundleError("INVALID_FIELD_INVARIANT_RECEIPT")
    if not (
        receipt.power_conservation_measured
        and receipt.full_field_roundtrip_measured
        and receipt.phase_only_power_matched
    ):
        raise VerificationBundleError("FIELD_INVARIANT_LANE_NOT_CLOSED")


def _require_current_conformance_lane(receipt: Mapping[str, object]) -> None:
    # Repaired PR620 verification re-executes the canonical producer and requires
    # exact consequence equality. A fresh hash over caller-authored findings fails.
    if not conformance.verify_conformance_receipt(receipt):
        raise VerificationBundleError("INVALID_OR_STALE_CONFORMANCE_RECEIPT")
    if receipt.get("imported_source_sha256") != EXPECTED_IMPORTED_SOURCE_SHA256:
        raise VerificationBundleError("CONFORMANCE_SOURCE_BINDING_MISMATCH")
    if receipt.get("producer_schema") != "AURA_K27_OPTICS_CANONICAL_CONFORMANCE_PRODUCER_V1":
        raise VerificationBundleError("CONFORMANCE_PRODUCER_GENERATION_REQUIRED")
    if receipt.get("software_independent_conformance_pass") is not True:
        raise VerificationBundleError("INDEPENDENT_CONFORMANCE_LANE_NOT_CLOSED")
    for key in (
        "caller_findings_accepted",
        "caller_source_sha_accepted",
        "caller_parent_ids_accepted",
    ):
        if receipt.get(key) is not False:
            raise VerificationBundleError("CONFORMANCE_CALLER_OVERRIDE_CEILING_WIDENED")


@dataclass(frozen=True)
class SpatialOpticsSoftwareVerificationBundleV2:
    invariant_receipt_sha256: str
    conformance_receipt_sha256: str
    invariant_semantic_generation: str
    conformance_semantic_generation: str
    conformance_owner_blob: str
    conformance_imported_source_sha256: str
    verification_lanes: tuple[str, str]
    field_invariant_measurement_pass: bool
    independent_formulation_conformance_pass: bool
    conformance_producer_traversed: bool
    historical_conformance_green_is_current_proof: bool
    verification_modes_distinct: bool
    same_test_object_proven: bool
    shared_implementation_generation_proven: bool
    shared_fixture_identity_proven: bool
    shared_sampling_grid_identity_proven: bool
    shared_source_identity_proven: bool
    physical_optics_validation_proven: bool
    hardware_performance_proven: bool
    optical_safety_proven: bool
    deployment_ready: bool
    semantic_k27_authority_proven: bool
    effect_authority_proven: bool
    gate10_promoted: bool
    native_transformer_kv_accessed: bool
    reopen_requirements: tuple[str, str, str, str]
    schema: str = SCHEMA

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @property
    def bundle_digest(self) -> str:
        return _digest(self.to_dict())

    @property
    def evidence_ref(self) -> str:
        return f"spatial-optics-software-verification-bundle-sha256:{self.bundle_digest}"


def build_software_verification_bundle(
    invariant_receipt: OpticalInvariantReceiptV1,
    conformance_receipt: Mapping[str, object],
) -> SpatialOpticsSoftwareVerificationBundleV2:
    _require_closed_invariant_lane(invariant_receipt)
    _require_current_conformance_lane(conformance_receipt)
    conformance_digest = conformance_receipt.get("receipt_sha256")
    if type(conformance_digest) is not str or len(conformance_digest) != 64:
        raise VerificationBundleError("CONFORMANCE_RECEIPT_IDENTITY_REQUIRED")

    return SpatialOpticsSoftwareVerificationBundleV2(
        invariant_receipt_sha256=invariant_receipt.receipt_sha256,
        conformance_receipt_sha256=conformance_digest,
        invariant_semantic_generation=INVARIANT_SEMANTIC_GENERATION,
        conformance_semantic_generation=CONFORMANCE_SEMANTIC_GENERATION,
        conformance_owner_blob=CONFORMANCE_OWNER_BLOB,
        conformance_imported_source_sha256=EXPECTED_IMPORTED_SOURCE_SHA256,
        verification_lanes=LANES,
        field_invariant_measurement_pass=True,
        independent_formulation_conformance_pass=True,
        conformance_producer_traversed=True,
        historical_conformance_green_is_current_proof=False,
        verification_modes_distinct=True,
        same_test_object_proven=False,
        shared_implementation_generation_proven=False,
        shared_fixture_identity_proven=False,
        shared_sampling_grid_identity_proven=False,
        shared_source_identity_proven=False,
        physical_optics_validation_proven=False,
        hardware_performance_proven=False,
        optical_safety_proven=False,
        deployment_ready=False,
        semantic_k27_authority_proven=False,
        effect_authority_proven=False,
        gate10_promoted=False,
        native_transformer_kv_accessed=False,
        reopen_requirements=REOPEN_REQUIREMENTS,
    )
