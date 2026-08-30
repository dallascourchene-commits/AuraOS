"""Bind W3 admission to the independently verified native synthetic proof plane.

D0 / nonpromoting convergence adapter.

This module does not execute GLM-5.3, read official tensor payloads, authorize a
provider/host effect, or infer G2.  It closes one narrower relation:

    native-synthetic-fixture eligibility
      + exact independently hosted PR406 fixture/oracle evidence
      -> admitted native synthetic W3 proof receipt

The numerical plane is bound to the exact semantic PR406 generation and hosted
run that exercised the selected-range fixture plus the discriminative
non-uniform FP8 scale oracle.  A later CODEMAP-only descendant does not replace
that semantic evidence generation.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Mapping

ADMISSION_SCHEMA = "AWJ032GLM53W3CompositeAdmissionV1"
FIXTURE_EVIDENCE_SCHEMA = "GLM53NativeSyntheticFixtureEvidenceV1"
SCHEMA = "AWJ032GLM53W3AdmittedSyntheticProofV1"

PR414_VERIFIED_HEAD = "aa00fb52b1cae0e0fa68b73554d81ef27d48887f"
PR414_VERIFIED_RUN_REF = "github-actions:run:33339184063:job:99331570908"
PR406_SEMANTIC_HEAD = "d518e0910a747ab83b6524bdcc49245076a0090c"
PR406_CODEMAP_ONLY_DESCENDANT = "107843a57ececb7565177f25e02b5256f132c67c"
PR406_VERIFIED_RUN_REF = "github-actions:run:33338674115:job:99330126260"
PR406_TOTAL_TESTS = 73

NEGATIVE_CONTROLS = (
    "GATE_UP_SCALE_COMPANION_SWAP",
    "DOWN_SCALE_ROW_MISINDEX",
    "IGNORED_ALL_ONES_SCALES",
    "SINGLE_SCALE_BLOCK_MUTATION",
)


class W3AdmittedSyntheticProofError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise W3AdmittedSyntheticProofError("NONCANONICAL_RECEIPT") from exc


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
    raise W3AdmittedSyntheticProofError(code)


def _exact_bool(value: Any, expected: bool, code: str) -> None:
    if type(value) is not bool or value is not expected:
        raise W3AdmittedSyntheticProofError(code)


@dataclass(frozen=True)
class NativeSyntheticFixtureEvidence:
    """Exact externally observed PR406 semantic evidence generation."""

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
        return {
            **asdict(self),
            "negative_controls_detected": list(self.negative_controls_detected),
        }

    @property
    def logical_id(self) -> str:
        return _digest(self.to_dict())


def verified_pr406_fixture_evidence() -> NativeSyntheticFixtureEvidence:
    """Return the pinned hosted PR406 fixture/oracle evidence generation."""
    return NativeSyntheticFixtureEvidence()


def _validate_admission(value: Any) -> tuple[dict[str, Any], str]:
    receipt = _as_mapping(value, "W3_COMPOSITE_ADMISSION_REQUIRED")
    if receipt.get("schema") != ADMISSION_SCHEMA:
        raise W3AdmittedSyntheticProofError("W3_COMPOSITE_SCHEMA_MISMATCH")
    if receipt.get("status") != "ELIGIBLE_FOR_NATIVE_SYNTHETIC_W3_FIXTURE":
        raise W3AdmittedSyntheticProofError("W3_NATIVE_FIXTURE_NOT_ELIGIBLE")
    if receipt.get("blockers") not in ([], ()):
        raise W3AdmittedSyntheticProofError("W3_ADMISSION_BLOCKER_REMAINS")

    for field in (
        "official_w2_producer_proof_consumed",
        "official_mtp_source_provenance_consumed",
        "native_synthetic_w3_eligible",
    ):
        _exact_bool(receipt.get(field), True, f"W3_REQUIRED_PROOF_MISSING:{field}")

    for field in (
        "official_tensor_payload_admitted",
        "runtime_execution_admitted",
        "g2_admitted",
        "provider_effect_admitted",
        "authority",
    ):
        _exact_bool(receipt.get(field), False, f"W3_EFFECT_CEILING_WIDENED:{field}")

    return receipt, _digest(receipt)


def _validate_fixture_evidence(value: Any) -> tuple[dict[str, Any], str]:
    evidence = _as_mapping(value, "PR406_FIXTURE_EVIDENCE_REQUIRED")
    expected = verified_pr406_fixture_evidence().to_dict()
    if evidence.get("schema") != FIXTURE_EVIDENCE_SCHEMA:
        raise W3AdmittedSyntheticProofError("PR406_FIXTURE_EVIDENCE_SCHEMA_MISMATCH")
    if set(evidence) != set(expected):
        raise W3AdmittedSyntheticProofError("PR406_FIXTURE_EVIDENCE_FIELD_SET_MISMATCH")

    for key, expected_value in expected.items():
        actual = evidence.get(key)
        if key == "negative_controls_detected" and isinstance(actual, tuple):
            actual = list(actual)
        if type(actual) is not type(expected_value) or actual != expected_value:
            raise W3AdmittedSyntheticProofError("PR406_FIXTURE_EVIDENCE_MISMATCH", key)

    return evidence, _digest(evidence)


@dataclass(frozen=True)
class W3AdmittedSyntheticProofReceipt:
    status: str
    blockers: tuple[str, ...]
    admission_receipt_digest: str
    fixture_evidence_digest: str
    pr414_verified_head: str = PR414_VERIFIED_HEAD
    pr414_verified_run_ref: str = PR414_VERIFIED_RUN_REF
    pr406_semantic_head: str = PR406_SEMANTIC_HEAD
    pr406_verified_run_ref: str = PR406_VERIFIED_RUN_REF
    official_w2_producer_proof_consumed: bool = True
    official_mtp_source_provenance_consumed: bool = True
    native_selected_range_fixture_proven: bool = True
    independent_scale_semantic_oracle_proven: bool = True
    negative_scale_controls_proven: bool = True
    native_synthetic_w3_proven: bool = True
    official_tensor_compatibility_proven: bool = False
    official_tensor_payload_admitted: bool = False
    runtime_mtp_support_proven: bool = False
    runtime_execution_admitted: bool = False
    g2_admitted: bool = False
    provider_effect_admitted: bool = False
    quality_proven: bool = False
    authority: bool = False
    schema: str = SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "blockers": list(self.blockers),
        }

    @property
    def logical_id(self) -> str:
        return _digest(self.to_dict())


def compose_admitted_native_synthetic_w3_proof(
    *,
    admission_receipt: Any,
    fixture_evidence: Any | None = None,
) -> W3AdmittedSyntheticProofReceipt:
    """Join exact W3 admission with the exact hosted PR406 synthetic proof plane."""
    _, admission_digest = _validate_admission(admission_receipt)
    if fixture_evidence is None:
        fixture_evidence = verified_pr406_fixture_evidence()
    _, fixture_digest = _validate_fixture_evidence(fixture_evidence)

    return W3AdmittedSyntheticProofReceipt(
        status="PROVEN_NATIVE_SYNTHETIC_W3_FIXTURE",
        blockers=(),
        admission_receipt_digest=admission_digest,
        fixture_evidence_digest=fixture_digest,
    )
