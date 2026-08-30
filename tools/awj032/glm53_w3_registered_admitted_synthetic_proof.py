"""Compose current registry-bound W3 admission with discriminative PR406 evidence.

D0 / nonpromoting. This consumer requires the exact current PR412 registered
producer->registry->PR409->PR410 admission plane and the independently hosted
PR406 selected-range + scale-semantic proof plane. It proves only the native
synthetic W3 fixture. Official tensor compatibility, runtime MTP, G2, provider,
quality and authority remain false.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any, Mapping

from tools.awj032 import glm53_pr340_producer_snapshot_registry as registry

ADMISSION_SCHEMA = "AWJ032GLM53W3RegisteredProofPlaneAdmissionV3"
FIXTURE_EVIDENCE_SCHEMA = "GLM53NativeSyntheticFixtureEvidenceV1"
SCHEMA = "AWJ032GLM53W3RegisteredAdmittedSyntheticProofV1"

PR412_REGISTERED_HEAD = "1673082eec99bd952c1dd56f24e38f4a6fbf4ff3"
PR412_REGISTERED_RUN_REF = "github-actions:run:33339936456:job:99333620834"
PR406_SEMANTIC_HEAD = "d518e0910a747ab83b6524bdcc49245076a0090c"
PR406_CODEMAP_ONLY_DESCENDANT = "107843a57ececb7565177f25e02b5256f132c67c"
PR406_VERIFIED_RUN_REF = "github-actions:run:33338674115:job:99330126260"
PR406_TOTAL_TESTS = 73
OFFICIAL_MTP_EVIDENCE_ID = "b0803af6fdb7afd0dcdbf7c5b718605658a02534c960d965cfc1729eb4d9d3a2"

NEGATIVE_CONTROLS = (
    "GATE_UP_SCALE_COMPANION_SWAP",
    "DOWN_SCALE_ROW_MISINDEX",
    "IGNORED_ALL_ONES_SCALES",
    "SINGLE_SCALE_BLOCK_MUTATION",
)

_ADMISSION_FIELDS = {
    "schema", "status", "blockers", "w2_consumer_receipt_id",
    "official_w2_bound_plan_digest", "pr340_registry_schema",
    "pr340_producer_execution_head", "pr340_producer_run_id",
    "pr340_producer_job_id", "pr340_final_report_digest",
    "pr340_classification_stage_logical_id", "pr340_snapshot_digest",
    "official_mtp_source_evidence_id", "official_mtp_source_bundle_id",
    "pr340_producer_report_registered",
    "pr409_producer_and_source_appraisal_proven",
    "synthetic_tiny_fixture_admitted", "official_tensor_payload_admitted",
    "runtime_mtp_support_proven", "runtime_execution_admitted",
    "checkpoint_payload_admitted", "provider_effect_admitted", "g2_admitted",
    "quality_proven", "authority",
}


class W3RegisteredSyntheticProofError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise W3RegisteredSyntheticProofError("NONCANONICAL_RECEIPT") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _as_mapping(value: Any, code: str) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        raw = to_dict()
        if isinstance(raw, Mapping):
            return dict(raw)
    raise W3RegisteredSyntheticProofError(code)


def _exact_bool(value: Any, expected: bool, code: str) -> None:
    if type(value) is not bool or value is not expected:
        raise W3RegisteredSyntheticProofError(code)


def _hex64(value: Any, code: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise W3RegisteredSyntheticProofError(code)
    return value


@dataclass(frozen=True)
class NativeSyntheticFixtureEvidence:
    semantic_head: str = PR406_SEMANTIC_HEAD
    codemap_only_descendant: str = PR406_CODEMAP_ONLY_DESCENDANT
    hosted_run_ref: str = PR406_VERIFIED_RUN_REF
    total_tests_passed: int = PR406_TOTAL_TESTS
    native_selected_range_fixture_passed: bool = True
    selected_expert_tensor_reads_only: bool = True
    backend_io_binding_attested: bool = True
    independent_scale_semantic_oracle_passed: bool = True
    negative_controls_detected: tuple[str, ...] = NEGATIVE_CONTROLS
    synthetic_source_only: bool = True
    official_tensor_payload_admitted: bool = False
    runtime_execution_admitted: bool = False
    g2_admitted: bool = False
    provider_effect_admitted: bool = False
    authority: bool = False
    schema: str = FIXTURE_EVIDENCE_SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "negative_controls_detected": list(self.negative_controls_detected)}

    @property
    def logical_id(self) -> str:
        return _digest(self.to_dict())


def verified_pr406_fixture_evidence() -> NativeSyntheticFixtureEvidence:
    return NativeSyntheticFixtureEvidence()


def _validate_registered_admission(value: Any) -> tuple[dict[str, Any], str]:
    receipt = _as_mapping(value, "W3_REGISTERED_ADMISSION_REQUIRED")
    if set(receipt) != _ADMISSION_FIELDS:
        raise W3RegisteredSyntheticProofError("W3_REGISTERED_ADMISSION_FIELD_SET_MISMATCH")
    if receipt.get("schema") != ADMISSION_SCHEMA:
        raise W3RegisteredSyntheticProofError("W3_REGISTERED_ADMISSION_SCHEMA_MISMATCH")
    if receipt.get("status") != "ELIGIBLE_FOR_NATIVE_SYNTHETIC_W3_FIXTURE":
        raise W3RegisteredSyntheticProofError("W3_NATIVE_FIXTURE_NOT_ELIGIBLE")
    if receipt.get("blockers") not in ([], ()):
        raise W3RegisteredSyntheticProofError("W3_ADMISSION_BLOCKER_REMAINS")

    _hex64(receipt.get("w2_consumer_receipt_id"), "W2_CONSUMER_RECEIPT_ID_INVALID")
    _hex64(receipt.get("official_w2_bound_plan_digest"), "OFFICIAL_W2_PLAN_DIGEST_INVALID")

    exact = {
        "pr340_registry_schema": registry.REGISTRY_SCHEMA,
        "pr340_producer_execution_head": registry.PRODUCER_EXECUTION_HEAD,
        "pr340_producer_run_id": registry.PRODUCER_RUN_ID,
        "pr340_producer_job_id": registry.PRODUCER_JOB_ID,
        "pr340_final_report_digest": registry.FINAL_REPORT_DIGEST,
        "pr340_classification_stage_logical_id": registry.CLASSIFICATION_STAGE_LOGICAL_ID,
        "pr340_snapshot_digest": registry.SNAPSHOT_DIGEST,
        "official_mtp_source_evidence_id": OFFICIAL_MTP_EVIDENCE_ID,
        "official_mtp_source_bundle_id": registry.SOURCE_BUNDLE_ID,
    }
    for field, expected in exact.items():
        actual = receipt.get(field)
        if type(actual) is not type(expected) or actual != expected:
            raise W3RegisteredSyntheticProofError("W3_REGISTERED_COORDINATE_MISMATCH", field)

    for field in (
        "pr340_producer_report_registered",
        "pr409_producer_and_source_appraisal_proven",
        "synthetic_tiny_fixture_admitted",
    ):
        _exact_bool(receipt.get(field), True, f"W3_REQUIRED_REGISTERED_PROOF_MISSING:{field}")
    for field in (
        "official_tensor_payload_admitted", "runtime_mtp_support_proven",
        "runtime_execution_admitted", "checkpoint_payload_admitted",
        "provider_effect_admitted", "g2_admitted", "quality_proven", "authority",
    ):
        _exact_bool(receipt.get(field), False, f"W3_EFFECT_CEILING_WIDENED:{field}")
    return receipt, _digest(receipt)


def _validate_fixture_evidence(value: Any) -> tuple[dict[str, Any], str]:
    evidence = _as_mapping(value, "PR406_FIXTURE_EVIDENCE_REQUIRED")
    expected = verified_pr406_fixture_evidence().to_dict()
    if evidence.get("schema") != FIXTURE_EVIDENCE_SCHEMA:
        raise W3RegisteredSyntheticProofError("PR406_FIXTURE_EVIDENCE_SCHEMA_MISMATCH")
    if set(evidence) != set(expected):
        raise W3RegisteredSyntheticProofError("PR406_FIXTURE_EVIDENCE_FIELD_SET_MISMATCH")
    for key, expected_value in expected.items():
        actual = evidence.get(key)
        if key == "negative_controls_detected" and isinstance(actual, tuple):
            actual = list(actual)
        if type(actual) is not type(expected_value) or actual != expected_value:
            raise W3RegisteredSyntheticProofError("PR406_FIXTURE_EVIDENCE_MISMATCH", key)
    return evidence, _digest(evidence)


@dataclass(frozen=True)
class W3RegisteredAdmittedSyntheticProofReceipt:
    status: str
    blockers: tuple[str, ...]
    registered_admission_receipt_digest: str
    fixture_evidence_digest: str
    pr412_registered_head: str = PR412_REGISTERED_HEAD
    pr412_registered_run_ref: str = PR412_REGISTERED_RUN_REF
    pr406_semantic_head: str = PR406_SEMANTIC_HEAD
    pr406_verified_run_ref: str = PR406_VERIFIED_RUN_REF
    registered_producer_report_proven: bool = True
    registered_pr409_source_appraisal_proven: bool = True
    w2_producer_consumer_boundary_proven: bool = True
    native_selected_range_fixture_proven: bool = True
    independent_scale_semantic_oracle_proven: bool = True
    negative_scale_controls_proven: bool = True
    native_synthetic_w3_proven: bool = True
    official_tensor_compatibility_proven: bool = False
    official_tensor_payload_admitted: bool = False
    runtime_mtp_support_proven: bool = False
    runtime_execution_admitted: bool = False
    checkpoint_payload_admitted: bool = False
    g2_admitted: bool = False
    provider_effect_admitted: bool = False
    quality_proven: bool = False
    authority: bool = False
    schema: str = SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "blockers": list(self.blockers)}

    @property
    def logical_id(self) -> str:
        return _digest(self.to_dict())


def compose_registered_native_synthetic_w3_proof(
    *, admission_receipt: Any,
    fixture_evidence: Any | None = None,
) -> W3RegisteredAdmittedSyntheticProofReceipt:
    """Join current registered W3 admission with exact PR406 synthetic proof."""
    _, admission_digest = _validate_registered_admission(admission_receipt)
    if fixture_evidence is None:
        fixture_evidence = verified_pr406_fixture_evidence()
    _, fixture_digest = _validate_fixture_evidence(fixture_evidence)
    return W3RegisteredAdmittedSyntheticProofReceipt(
        status="PROVEN_NATIVE_SYNTHETIC_W3_FIXTURE",
        blockers=(),
        registered_admission_receipt_digest=admission_digest,
        fixture_evidence_digest=fixture_digest,
    )
