"""ZF-06C evidence-digest and zero-baseline preflight for the canonical ZF-06 assessor.

This does not own storage/mechanism disposition. It validates evidence bindings and
unadmitted newly introduced burdens, then delegates disposition to the canonical
``low_storage_mechanism_assessment.assess`` function.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields
import hashlib
import json
import re
from typing import Any, Mapping

from tools.aura_adopt.low_storage_mechanism_assessment import (
    AssessmentError,
    MechanismEvidence,
    MetricSet,
    assess,
)

SCHEMA = "LowStorageEvidencePreflightV1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _text(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AssessmentError(code)
    return value.strip()


def _sha(value: Any, code: str) -> str:
    value = _text(value, code).lower()
    if not _SHA256.fullmatch(value):
        raise AssessmentError(code)
    return value


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()


def _digest(domain: str, value: Any) -> str:
    return hashlib.sha256(domain.encode() + b"\0" + _canonical(value)).hexdigest()


@dataclass(frozen=True)
class ExternalEvidenceBindingV1:
    evidence_ref: str
    evidence_digest: str
    source_generation: str
    currentness_ref: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_ref", _text(self.evidence_ref, "EVIDENCE_REF_REQUIRED"))
        object.__setattr__(self, "evidence_digest", _sha(self.evidence_digest, "EVIDENCE_DIGEST_INVALID"))
        object.__setattr__(self, "source_generation", _text(self.source_generation, "EVIDENCE_SOURCE_GENERATION_REQUIRED"))
        object.__setattr__(self, "currentness_ref", _text(self.currentness_ref, "EVIDENCE_CURRENTNESS_REF_REQUIRED"))


def _bind_path(e: MechanismEvidence, binding: ExternalEvidenceBindingV1) -> None:
    path = e.path_evidence
    if binding.evidence_ref != path.evidence_ref:
        raise AssessmentError("PATH_EVIDENCE_REF_MISMATCH")
    if binding.source_generation != path.source_generation:
        raise AssessmentError("PATH_EVIDENCE_GENERATION_MISMATCH")
    if binding.currentness_ref != path.currentness_ref:
        raise AssessmentError("PATH_EVIDENCE_CURRENTNESS_MISMATCH")


def _bind_host(e: MechanismEvidence, binding: ExternalEvidenceBindingV1 | None) -> None:
    host = e.host_evidence
    if host is None:
        if binding is not None:
            raise AssessmentError("UNEXPECTED_HOST_EVIDENCE_BINDING")
        return
    if binding is None:
        raise AssessmentError("HOST_EVIDENCE_DIGEST_BINDING_REQUIRED")
    if binding.evidence_ref != host.witness_ref:
        raise AssessmentError("HOST_EVIDENCE_REF_MISMATCH")
    if binding.source_generation != host.source_generation:
        raise AssessmentError("HOST_EVIDENCE_GENERATION_MISMATCH")
    if binding.currentness_ref != host.currentness_ref:
        raise AssessmentError("HOST_EVIDENCE_CURRENTNESS_MISMATCH")


def _all_zero_baseline_added_burdens(candidate: MetricSet, baseline: MetricSet) -> tuple[str, ...]:
    excluded = {"logical_payload_bytes", "encoded_or_retained_bytes"}
    return tuple(sorted(
        f.name
        for f in fields(MetricSet)
        if f.name not in excluded
        and getattr(baseline, f.name) == 0
        and getattr(candidate, f.name) is not None
        and getattr(candidate, f.name) > 0
    ))


def preflight_assess(
    evidence: MechanismEvidence,
    *,
    path_binding: ExternalEvidenceBindingV1,
    host_binding: ExternalEvidenceBindingV1 | None = None,
) -> Mapping[str, Any]:
    if not isinstance(evidence, MechanismEvidence):
        raise AssessmentError("MECHANISM_EVIDENCE_REQUIRED")
    if not isinstance(path_binding, ExternalEvidenceBindingV1):
        raise AssessmentError("PATH_EVIDENCE_DIGEST_BINDING_REQUIRED")
    if host_binding is not None and not isinstance(host_binding, ExternalEvidenceBindingV1):
        raise AssessmentError("HOST_EVIDENCE_DIGEST_BINDING_INVALID")

    _bind_path(evidence, path_binding)
    _bind_host(evidence, host_binding)

    all_added = _all_zero_baseline_added_burdens(evidence.candidate, evidence.baseline)
    undeclared = tuple(sorted(set(all_added) - set(evidence.required_metrics)))
    if undeclared:
        raise AssessmentError("ZERO_BASELINE_BURDEN_NOT_ADMITTED", ",".join(undeclared))

    canonical = assess(evidence)
    if canonical.get("effect_authorized") is not False:
        raise AssessmentError("CANONICAL_ASSESSMENT_AUTHORITY_WIDENING")
    if canonical.get("device_viability_proven") is not False:
        raise AssessmentError("CANONICAL_DEVICE_VIABILITY_WIDENING")

    logical = {
        "schema": SCHEMA,
        "canonical_assessment_logical_id": _text(canonical.get("logical_id"), "CANONICAL_LOGICAL_ID_REQUIRED"),
        "path_binding": asdict(path_binding),
        "host_binding": asdict(host_binding) if host_binding else None,
        "all_zero_baseline_added_burdens": all_added,
        "required_metrics": tuple(evidence.required_metrics),
        "effect_authorized": False,
        "device_viability_proven": False,
        "evidence_authenticated": False,
    }
    return {
        **logical,
        "preflight_digest": _digest("LOW_STORAGE_EVIDENCE_PREFLIGHT_V1", logical),
        "canonical_assessment": canonical,
        "claim_ceiling": "EVIDENCE_BINDING_PREFLIGHT_ONLY_NO_BENCHMARK_OR_DEVICE_AUTHORITY",
    }
