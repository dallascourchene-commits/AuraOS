"""Canonical-owner plus discriminative-native-fixture W3 proof.

D0/nonpromoting. This consumes the current PR427 canonical-owner admission and
an exact receipt for the PR406 semantic test generation. It proves only the
native synthetic W3 fixture. Official tensor compatibility, runtime MTP,
quality, G2, provider effects and authority remain false.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any

from tools.awj032.glm53_w3_canonical_owner_composite import (
    PR410_CURRENT_HEAD,
    PR410_VERIFIED_JOB_ID,
    PR410_VERIFIED_RUN_ID,
    PR410_VERIFIED_SEMANTIC_HEAD,
    PR421_JOB_ID,
    PR421_OBSERVATION_HEAD,
    PR421_REPORT_LOGICAL_ID,
    PR421_RUN_ID,
    PR421_SEMANTIC_HEAD,
    W3CanonicalOwnerCompositeReceipt,
)

SCHEMA = "AWJ032GLM53W3CanonicalOwnerSyntheticProofV1"
PR427_HEAD = "b0467c844f0836344b81dc4135a994b188d9e2f1"
PR427_RUN_ID = 33340650293
PR427_JOB_ID = 99335569489

PR406_SEMANTIC_HEAD = "d518e0910a747ab83b6524bdcc49245076a0090c"
PR406_CURRENT_HEAD = "107843a57ececb7565177f25e02b5256f132c67c"
PR406_NATIVE_FIXTURE_TEST_BLOB = "80471d603ba9b4b17a44e130f4870fb19372b15a"
PR406_SCALE_ORACLE_TEST_BLOB = "92a31df1e3b6abb0944a0cae58fb08eb3d2662aa"
NEGATIVE_CONTROLS = (
    "GATE_UP_SCALE_COMPANION_SWAP",
    "DOWN_SCALE_ROW_MISINDEX",
    "IGNORED_ALL_ONES_SCALES",
    "SINGLE_SCALE_BLOCK_MUTATION",
)


class CanonicalOwnerSyntheticProofError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}:{detail}" if detail else code)
        self.code = code
        self.detail = detail


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _exact_bool(value: Any, expected: bool, code: str) -> None:
    if type(value) is not bool or value is not expected:
        raise CanonicalOwnerSyntheticProofError(code)


@dataclass(frozen=True)
class PR406DiscriminativeNumericalEvidence:
    semantic_head: str = PR406_SEMANTIC_HEAD
    current_head: str = PR406_CURRENT_HEAD
    native_fixture_test_blob: str = PR406_NATIVE_FIXTURE_TEST_BLOB
    scale_oracle_test_blob: str = PR406_SCALE_ORACLE_TEST_BLOB
    native_selected_range_fixture_passed: bool = True
    selected_expert_tensor_reads_only: bool = True
    backend_io_binding_attested: bool = True
    independent_scale_semantic_oracle_passed: bool = True
    negative_controls_detected: tuple[str, ...] = NEGATIVE_CONTROLS
    synthetic_source_only: bool = True
    official_tensor_payload_admitted: bool = False
    runtime_execution_admitted: bool = False
    quality_proven: bool = False
    g2_admitted: bool = False
    provider_effect_admitted: bool = False
    authority: bool = False

    @property
    def evidence_digest(self) -> str:
        return _digest({**asdict(self), "negative_controls_detected": list(self.negative_controls_detected)})


CANONICAL_PR406_NUMERICAL_EVIDENCE = PR406DiscriminativeNumericalEvidence()


def _validate_admission(value: Any) -> W3CanonicalOwnerCompositeReceipt:
    if not isinstance(value, W3CanonicalOwnerCompositeReceipt):
        raise CanonicalOwnerSyntheticProofError("PR427_CANONICAL_OWNER_ADMISSION_REQUIRED")
    if value.schema != "AWJ032GLM53W3CanonicalOwnerCompositeV1":
        raise CanonicalOwnerSyntheticProofError("PR427_ADMISSION_SCHEMA_MISMATCH")
    if value.status != "ELIGIBLE_FOR_NATIVE_SYNTHETIC_W3_FIXTURE" or value.blockers != ():
        raise CanonicalOwnerSyntheticProofError("PR427_NATIVE_FIXTURE_ELIGIBILITY_REQUIRED")
    expected = {
        "pr410_current_head": PR410_CURRENT_HEAD,
        "pr410_verified_semantic_head": PR410_VERIFIED_SEMANTIC_HEAD,
        "pr410_verified_run_id": PR410_VERIFIED_RUN_ID,
        "pr410_verified_job_id": PR410_VERIFIED_JOB_ID,
        "pr421_semantic_head": PR421_SEMANTIC_HEAD,
        "pr421_observation_head": PR421_OBSERVATION_HEAD,
        "pr421_run_id": PR421_RUN_ID,
        "pr421_job_id": PR421_JOB_ID,
        "pr421_report_logical_id": PR421_REPORT_LOGICAL_ID,
    }
    for field, expected_value in expected.items():
        actual = getattr(value, field)
        if type(actual) is not type(expected_value) or actual != expected_value:
            raise CanonicalOwnerSyntheticProofError("PR427_OWNER_COORDINATE_MISMATCH", field)
    for field in ("official_w2_producer_proof_consumed", "registry_bound_mtp_owner_consumed", "native_synthetic_w3_eligible"):
        _exact_bool(getattr(value, field), True, f"PR427_REQUIRED_PROOF_MISSING:{field}")
    for field in (
        "native_synthetic_w3_numerical_proven", "official_tensor_payload_admitted",
        "runtime_execution_admitted", "quality_proven", "g2_admitted",
        "provider_effect_admitted", "authority",
    ):
        _exact_bool(getattr(value, field), False, f"PR427_EFFECT_CEILING_WIDENED:{field}")
    return value


def _validate_numerical(value: Any) -> PR406DiscriminativeNumericalEvidence:
    if not isinstance(value, PR406DiscriminativeNumericalEvidence):
        raise CanonicalOwnerSyntheticProofError("PR406_NUMERICAL_EVIDENCE_REQUIRED")
    if value != CANONICAL_PR406_NUMERICAL_EVIDENCE:
        raise CanonicalOwnerSyntheticProofError("PR406_NUMERICAL_EVIDENCE_MISMATCH")
    for field in (
        "native_selected_range_fixture_passed", "selected_expert_tensor_reads_only",
        "backend_io_binding_attested", "independent_scale_semantic_oracle_passed",
        "synthetic_source_only",
    ):
        _exact_bool(getattr(value, field), True, f"PR406_REQUIRED_NUMERICAL_PROOF_MISSING:{field}")
    for field in (
        "official_tensor_payload_admitted", "runtime_execution_admitted", "quality_proven",
        "g2_admitted", "provider_effect_admitted", "authority",
    ):
        _exact_bool(getattr(value, field), False, f"PR406_EFFECT_CEILING_WIDENED:{field}")
    return value


@dataclass(frozen=True)
class W3CanonicalOwnerSyntheticProofReceipt:
    status: str
    blockers: tuple[str, ...]
    canonical_owner_admission_logical_id: str
    pr406_numerical_evidence_digest: str
    pr427_head: str = PR427_HEAD
    pr427_run_id: int = PR427_RUN_ID
    pr427_job_id: int = PR427_JOB_ID
    pr406_semantic_head: str = PR406_SEMANTIC_HEAD
    pr406_current_head: str = PR406_CURRENT_HEAD
    canonical_owner_admission_proven: bool = True
    native_selected_range_fixture_proven: bool = True
    independent_scale_semantic_oracle_proven: bool = True
    negative_scale_controls_proven: bool = True
    native_synthetic_w3_proven: bool = True
    official_tensor_compatibility_proven: bool = False
    official_tensor_payload_admitted: bool = False
    runtime_mtp_support_proven: bool = False
    runtime_execution_admitted: bool = False
    checkpoint_payload_admitted: bool = False
    quality_proven: bool = False
    g2_admitted: bool = False
    provider_effect_admitted: bool = False
    authority: bool = False
    schema: str = SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "blockers": list(self.blockers)}

    @property
    def logical_id(self) -> str:
        return _digest(self.to_dict())


def prove_canonical_native_synthetic_w3(
    *,
    canonical_owner_admission: Any,
    numerical_evidence: Any = CANONICAL_PR406_NUMERICAL_EVIDENCE,
) -> W3CanonicalOwnerSyntheticProofReceipt:
    admission = _validate_admission(canonical_owner_admission)
    numerical = _validate_numerical(numerical_evidence)
    return W3CanonicalOwnerSyntheticProofReceipt(
        status="PROVEN_NATIVE_SYNTHETIC_W3_FIXTURE",
        blockers=(),
        canonical_owner_admission_logical_id=admission.logical_id,
        pr406_numerical_evidence_digest=numerical.evidence_digest,
    )
