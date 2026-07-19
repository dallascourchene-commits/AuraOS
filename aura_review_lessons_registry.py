"""Strict registry validation, detector dispatch, and Crucible replay."""
from __future__ import annotations

from collections.abc import Mapping
from datetime import date
import json
import math
from pathlib import Path
import re
from typing import Any

from aura_review_lessons_contracts import (
    _MAX_REVIEW_PAYLOAD_BYTES,
    _MAX_SCENARIO_BYTES,
    DEFAULT_REGISTRY_PATH,
    PATCH_AUTHORITY,
    REGISTRY_VERSION,
    ReviewLessonError,
    _bounded_json,
    _digest,
    _is_sequence,
)
from aura_review_lessons_determinism import (
    detect_implicit_coordinate_basis_change,
    detect_nested_unit_double_application,
    detect_noncanonical_interchange_acceptance,
    detect_order_dependent_digesting,
    detect_truncate_before_sort,
)
from aura_review_lessons_security import (
    detect_authority_aliases,
    detect_count_without_byte_budget,
    detect_noncanonical_source_path,
    detect_protected_metadata_overrides,
    detect_schema_runtime_drift,
    detect_stale_evidence_claim,
    detect_unwired_regression,
    detect_uri_alias_encoding,
)

DETECTORS = {
    function.__name__: function
    for function in (
        detect_authority_aliases, detect_protected_metadata_overrides,
        detect_order_dependent_digesting, detect_truncate_before_sort,
        detect_count_without_byte_budget, detect_noncanonical_source_path,
        detect_uri_alias_encoding, detect_schema_runtime_drift,
        detect_unwired_regression, detect_stale_evidence_claim,
        detect_implicit_coordinate_basis_change,
        detect_nested_unit_double_application,
        detect_noncanonical_interchange_acceptance,
    )
}

_TOP_LEVEL_FIELDS = {
    "version", "source_pr", "repository_head", "merge_commit", "created_at",
    "truth_boundary", "authority", "lessons", "scenarios", "registry_digest",
}
_AUTHORITY_ENVELOPE = {
    "production_mutation": False,
    "automatic_fix": False,
    "automatic_commit": False,
    "automatic_push": False,
    "automatic_pull_request": False,
    "automatic_merge": False,
    "human_review_required": True,
    "patch_authority": PATCH_AUTHORITY,
    "vsa_patch_authority": False,
}
_LESSON_FIELDS = {
    "lesson_id", "detector_id", "defect_class", "trigger", "invariant",
    "repair_pattern", "required_regression", "generalization_scope",
    "false_positive_guard", "provenance", "confidence",
}
_SCENARIO_FIELDS = {
    "scenario_id", "detector_id", "candidate", "expected_finding_code", "code_slice",
}
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

def _require_string(value: Any, *, field: str, minimum: int = 1, maximum: int) -> str:
    if not isinstance(value, str) or not minimum <= len(value) <= maximum:
        raise ReviewLessonError(f"{field} must be a string of length {minimum}..{maximum}")
    return value

def _require_string_array(value: Any, *, field: str) -> list[str]:
    if not _is_sequence(value) or not 1 <= len(value) <= 50:
        raise ReviewLessonError(f"{field} must contain 1..50 strings")
    result = [_require_string(item, field=field, maximum=500) for item in value]
    if len(result) != len(set(result)):
        raise ReviewLessonError(f"{field} values must be unique")
    return result

def validate_review_lesson_registry(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate every runtime constraint declared by the interchange schema."""

    if not isinstance(value, Mapping):
        raise ReviewLessonError("review lesson registry must be an object")
    _bounded_json(value, maximum=_MAX_REVIEW_PAYLOAD_BYTES, label="review lesson registry")
    if set(value) != _TOP_LEVEL_FIELDS:
        missing = _TOP_LEVEL_FIELDS - set(value)
        unexpected = set(value) - _TOP_LEVEL_FIELDS
        raise ReviewLessonError(
            f"review lesson registry keys mismatch: missing={sorted(missing)} "
            f"unexpected={sorted(unexpected)}"
        )
    if value.get("version") != REGISTRY_VERSION:
        raise ReviewLessonError("unsupported review lesson registry version")
    source_pr = value.get("source_pr")
    if isinstance(source_pr, bool) or not isinstance(source_pr, int) or source_pr < 1:
        raise ReviewLessonError("source_pr must be a positive integer")
    for field in ("repository_head", "merge_commit", "registry_digest"):
        if not isinstance(value.get(field), str) or not _SHA_RE.fullmatch(value[field]):
            raise ReviewLessonError(f"{field} must be a lowercase 40-character SHA")
    created_at = value.get("created_at")
    if not isinstance(created_at, str) or not _DATE_RE.fullmatch(created_at):
        raise ReviewLessonError("created_at must be YYYY-MM-DD")
    try:
        date.fromisoformat(created_at)
    except ValueError as exc:
        raise ReviewLessonError("created_at must be a valid calendar date") from exc
    if value.get("truth_boundary") != "review_learning_only":
        raise ReviewLessonError("truth_boundary must be review_learning_only")
    authority = value.get("authority")
    if not isinstance(authority, Mapping) or dict(authority) != _AUTHORITY_ENVELOPE:
        raise ReviewLessonError("review lesson authority envelope mismatch")

    lessons = value.get("lessons")
    scenarios = value.get("scenarios")
    if not _is_sequence(lessons) or not 1 <= len(lessons) <= 100:
        raise ReviewLessonError("registry lessons must contain 1..100 objects")
    if not _is_sequence(scenarios) or not 1 <= len(scenarios) <= 200:
        raise ReviewLessonError("registry scenarios must contain 1..200 objects")

    lesson_ids: set[str] = set()
    detector_ids: set[str] = set()
    canonical_lessons: list[dict[str, Any]] = []
    for raw in lessons:
        if not isinstance(raw, Mapping) or set(raw) != _LESSON_FIELDS:
            raise ReviewLessonError("each review lesson must match the strict lesson fields")
        lesson = dict(raw)
        lesson_id = lesson["lesson_id"]
        detector_id = lesson["detector_id"]
        if not isinstance(lesson_id, str):
            raise ReviewLessonError("lesson_id must be a string")
        if not isinstance(detector_id, str):
            raise ReviewLessonError("detector_id must be a string")
        if not re.fullmatch(r"PR164-CW-[A-Z]+-[0-9]{3}", lesson_id):
            raise ReviewLessonError(f"invalid lesson_id: {lesson_id}")
        if not re.fullmatch(r"detect_[a-z0-9_]+", detector_id):
            raise ReviewLessonError(f"invalid detector_id: {detector_id}")
        if lesson_id in lesson_ids:
            raise ReviewLessonError("lesson IDs must be non-empty and unique")
        if detector_id not in DETECTORS:
            raise ReviewLessonError(f"unknown detector_id: {detector_id}")
        lesson_ids.add(lesson_id)
        detector_ids.add(detector_id)
        _require_string(lesson["defect_class"], field="defect_class", maximum=200)
        for field, maximum in (
            ("trigger", 2000),
            ("invariant", 2000),
            ("repair_pattern", 3000),
            ("required_regression", 3000),
            ("false_positive_guard", 2000),
        ):
            _require_string(lesson[field], field=field, maximum=maximum)
        _require_string_array(lesson["generalization_scope"], field="generalization_scope")
        provenance = lesson["provenance"]
        if not isinstance(provenance, Mapping) or set(provenance) != {"pr_number", "reviewers", "paths"}:
            raise ReviewLessonError(f"lesson {lesson_id} provenance is invalid")
        if provenance.get("pr_number") != 164:
            raise ReviewLessonError(f"lesson {lesson_id} provenance pr_number must be 164")
        _require_string_array(provenance["reviewers"], field="provenance.reviewers")
        _require_string_array(provenance["paths"], field="provenance.paths")
        confidence = lesson["confidence"]
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            raise ReviewLessonError(f"lesson {lesson_id} confidence must be numeric")
        if not math.isfinite(float(confidence)) or not 0.0 <= float(confidence) <= 1.0:
            raise ReviewLessonError(f"lesson {lesson_id} confidence is outside [0,1]")
        canonical_lessons.append(lesson)

    canonical_scenarios: list[dict[str, Any]] = []
    scenario_ids: set[str] = set()
    for raw in scenarios:
        if not isinstance(raw, Mapping) or set(raw) != _SCENARIO_FIELDS:
            raise ReviewLessonError("each review scenario must match the strict scenario fields")
        scenario = dict(raw)
        scenario_id = scenario["scenario_id"]
        detector_id = scenario["detector_id"]
        expected = scenario["expected_finding_code"]
        if not isinstance(scenario_id, str):
            raise ReviewLessonError("scenario_id must be a string")
        if not isinstance(detector_id, str):
            raise ReviewLessonError("detector_id must be a string")
        if not isinstance(expected, str):
            raise ReviewLessonError("expected_finding_code must be a string")
        if not re.fullmatch(r"[a-z0-9-]+", scenario_id):
            raise ReviewLessonError(f"invalid scenario_id: {scenario_id}")
        if not re.fullmatch(r"detect_[a-z0-9_]+", detector_id):
            raise ReviewLessonError(f"invalid detector_id: {detector_id}")
        if not re.fullmatch(r"[A-Z0-9_]+", expected):
            raise ReviewLessonError(f"invalid expected_finding_code: {expected}")
        if scenario_id in scenario_ids:
            raise ReviewLessonError("scenario IDs must be non-empty and unique")
        if detector_id not in detector_ids:
            raise ReviewLessonError(f"scenario detector has no lesson: {detector_id}")
        _bounded_json(scenario, maximum=_MAX_SCENARIO_BYTES, label=f"scenario {scenario_id}")
        scenario_ids.add(scenario_id)
        canonical_scenarios.append(scenario)

    result = dict(value)
    result["lessons"] = sorted(canonical_lessons, key=lambda item: str(item["lesson_id"]))
    result["scenarios"] = sorted(canonical_scenarios, key=lambda item: str(item["scenario_id"]))
    supplied_digest = result.pop("registry_digest")
    canonical_digest = _digest(result, size=20)
    if supplied_digest != canonical_digest:
        raise ReviewLessonError("review lesson registry digest mismatch")
    result["registry_digest"] = canonical_digest
    return result


def load_review_lesson_registry(path: str | Path = DEFAULT_REGISTRY_PATH) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_review_lesson_registry(value)

__all__ = ["DETECTORS", "load_review_lesson_registry", "validate_review_lesson_registry"]
