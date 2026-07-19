"""Typed PR-review lessons, detectors, Crucible replay, and durable engine.

External reviewers are teacher signals, never patch authority. This facade
composes bounded contracts, deterministic detector packs, review normalization,
and the repository-bound lesson engine without granting mutation authority.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
import math
from pathlib import Path
import re
from typing import Any

from aura_review_lessons_contracts import (
    _MAX_REVIEW_PAYLOAD_BYTES,
    _MAX_SCENARIO_BYTES,
    CRUCIBLE_REPLAY_VERSION,
    DEFAULT_LEARNING_ROOT,
    DEFAULT_REGISTRY_PATH,
    PATCH_AUTHORITY,
    REGISTRY_VERSION,
    REVIEW_FINDING_VERSION,
    REVIEW_LESSON_VERSION,
    VSA_PATCH_AUTHORITY,
    ReviewLessonError,
    _bounded_json,
    _canonical_json,
    _digest,
    _git_head,
    _is_sequence,
    _safe_repo_path,
)
from aura_review_lessons_determinism import (
    detect_implicit_coordinate_basis_change,
    detect_nested_unit_double_application,
    detect_noncanonical_interchange_acceptance,
    detect_order_dependent_digesting,
    detect_truncate_before_sort,
    scan_source_for_review_lessons,
)
from aura_review_lessons_external import normalize_external_review
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


def validate_review_lesson_registry(value: Mapping[str, Any]) -> dict[str, Any]:
    """Runtime semantic validation for the strict lesson registry."""

    if not isinstance(value, Mapping):
        raise ReviewLessonError("review lesson registry must be an object")
    _bounded_json(value, maximum=_MAX_REVIEW_PAYLOAD_BYTES, label="review lesson registry")
    unexpected = set(value) - _TOP_LEVEL_FIELDS
    required = _TOP_LEVEL_FIELDS - {"registry_digest"}
    missing = required - set(value)
    if unexpected or missing:
        raise ReviewLessonError(
            f"review lesson registry keys mismatch: missing={sorted(missing)} "
            f"unexpected={sorted(unexpected)}"
        )
    if value.get("version") != REGISTRY_VERSION:
        raise ReviewLessonError("unsupported review lesson registry version")
    if int(value.get("source_pr") or 0) < 1:
        raise ReviewLessonError("source_pr must be a positive integer")
    for field in ("repository_head", "merge_commit"):
        if not _SHA_RE.fullmatch(str(value.get(field) or "")):
            raise ReviewLessonError(f"{field} must be a lowercase 40-character SHA")
    if not _DATE_RE.fullmatch(str(value.get("created_at") or "")):
        raise ReviewLessonError("created_at must be YYYY-MM-DD")
    if value.get("truth_boundary") != "review_learning_only":
        raise ReviewLessonError("truth_boundary must be review_learning_only")
    authority = value.get("authority")
    if not isinstance(authority, Mapping) or dict(authority) != _AUTHORITY_ENVELOPE:
        raise ReviewLessonError("review lesson authority envelope mismatch")
    lessons = value.get("lessons")
    scenarios = value.get("scenarios")
    if not _is_sequence(lessons) or not _is_sequence(scenarios):
        raise ReviewLessonError("registry lessons and scenarios must be arrays")
    lesson_ids: set[str] = set()
    detector_ids: set[str] = set()
    canonical_lessons: list[dict[str, Any]] = []
    for raw in lessons:
        if not isinstance(raw, Mapping):
            raise ReviewLessonError("each lesson must be an object")
        lesson = dict(raw)
        if set(lesson) != _LESSON_FIELDS:
            raise ReviewLessonError("review lesson keys mismatch")
        lesson_id = str(lesson.get("lesson_id") or "")
        detector_id = str(lesson.get("detector_id") or "")
        if not lesson_id or lesson_id in lesson_ids:
            raise ReviewLessonError("lesson IDs must be non-empty and unique")
        if detector_id not in DETECTORS:
            raise ReviewLessonError(f"unknown detector_id: {detector_id}")
        lesson_ids.add(lesson_id)
        detector_ids.add(detector_id)
        for key in (
            "trigger",
            "invariant",
            "repair_pattern",
            "required_regression",
            "generalization_scope",
            "false_positive_guard",
            "provenance",
        ):
            if key not in lesson:
                raise ReviewLessonError(f"lesson {lesson_id} missing {key}")
        scope = lesson.get("generalization_scope")
        if not _is_sequence(scope) or not scope or len(scope) != len(set(map(str, scope))):
            raise ReviewLessonError(f"lesson {lesson_id} generalization_scope must be unique strings")
        provenance = lesson.get("provenance")
        if not isinstance(provenance, Mapping) or set(provenance) != {"pr_number", "reviewers", "paths"}:
            raise ReviewLessonError(f"lesson {lesson_id} provenance is invalid")
        if int(provenance.get("pr_number") or 0) != int(value.get("source_pr") or 0):
            raise ReviewLessonError(f"lesson {lesson_id} provenance PR mismatch")
        for field in ("reviewers", "paths"):
            entries = provenance.get(field)
            if not _is_sequence(entries) or not entries or any(not str(item).strip() for item in entries):
                raise ReviewLessonError(f"lesson {lesson_id} provenance {field} is invalid")
        confidence = float(lesson.get("confidence") or 0.0)
        if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
            raise ReviewLessonError(f"lesson {lesson_id} confidence is outside [0,1]")
        canonical_lessons.append(lesson)
    canonical_scenarios: list[dict[str, Any]] = []
    scenario_ids: set[str] = set()
    for raw in scenarios:
        if not isinstance(raw, Mapping):
            raise ReviewLessonError("each scenario must be an object")
        scenario = dict(raw)
        if set(scenario) != _SCENARIO_FIELDS:
            raise ReviewLessonError("review scenario keys mismatch")
        scenario_id = str(scenario.get("scenario_id") or "")
        detector_id = str(scenario.get("detector_id") or "")
        if not scenario_id or scenario_id in scenario_ids:
            raise ReviewLessonError("scenario IDs must be non-empty and unique")
        if detector_id not in detector_ids:
            raise ReviewLessonError(f"scenario detector has no lesson: {detector_id}")
        _bounded_json(scenario, maximum=_MAX_SCENARIO_BYTES, label=f"scenario {scenario_id}")
        scenario_ids.add(scenario_id)
        canonical_scenarios.append(scenario)
    lesson_order = [str(item["lesson_id"]) for item in canonical_lessons]
    scenario_order = [str(item["scenario_id"]) for item in canonical_scenarios]
    if lesson_order != sorted(lesson_order) or scenario_order != sorted(scenario_order):
        raise ReviewLessonError("review lesson registry arrays must be canonically sorted")
    result = dict(value)
    result["lessons"] = sorted(canonical_lessons, key=lambda item: str(item["lesson_id"]))
    result["scenarios"] = sorted(canonical_scenarios, key=lambda item: str(item["scenario_id"]))
    supplied_digest = str(result.pop("registry_digest", "") or "")
    canonical_digest = _digest(result, size=20)
    if supplied_digest and supplied_digest != canonical_digest:
        raise ReviewLessonError("review lesson registry digest mismatch")
    result["registry_digest"] = canonical_digest
    return result


def load_review_lesson_registry(path: str | Path = DEFAULT_REGISTRY_PATH) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_review_lesson_registry(value)


def run_review_detector(detector_id: str, candidate: Any) -> dict[str, Any]:
    detector = DETECTORS.get(detector_id)
    if detector is None:
        raise ReviewLessonError(f"unknown review detector: {detector_id}")
    _bounded_json(candidate, maximum=_MAX_SCENARIO_BYTES, label="review detector candidate")
    findings = detector(candidate)
    packet = {
        "version": REVIEW_LESSON_VERSION,
        "detector_id": detector_id,
        "finding_count": len(findings),
        "findings": findings,
        "production_mutation": False,
        "automatic_fix": False,
        "automatic_commit": False,
        "automatic_push": False,
        "automatic_pull_request": False,
        "automatic_merge": False,
        "human_review_required": True,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
    packet["packet_digest"] = _digest(packet, size=16)
    return packet


def run_crucible_replay(
    registry: Mapping[str, Any] | str | Path = DEFAULT_REGISTRY_PATH,
    *,
    detector_ids: Sequence[str] = (),
) -> dict[str, Any]:
    """Replay typed adversarial lessons and emit proof-oriented receipts."""

    if isinstance(registry, (str, Path)):
        loaded = load_review_lesson_registry(registry)
    else:
        loaded = validate_review_lesson_registry(registry)
    selected = {str(value) for value in detector_ids if str(value)}
    unknown = selected - set(DETECTORS)
    if unknown:
        raise ReviewLessonError(f"unknown selected review detectors: {sorted(unknown)}")
    lessons = {str(item["detector_id"]): dict(item) for item in loaded["lessons"]}
    receipts: list[dict[str, Any]] = []
    for scenario in loaded["scenarios"]:
        detector_id = str(scenario["detector_id"])
        if selected and detector_id not in selected:
            continue
        lesson = lessons[detector_id]
        result = run_review_detector(detector_id, scenario.get("candidate"))
        expected_code = str(scenario.get("expected_finding_code") or "")
        matching = [
            finding
            for finding in result["findings"]
            if not expected_code or finding.get("code") == expected_code
        ]
        receipt = {
            "version": CRUCIBLE_REPLAY_VERSION,
            "scenario_id": scenario["scenario_id"],
            "lesson_invoked": lesson["lesson_id"],
            "detector_id": detector_id,
            "finding_produced": bool(matching),
            "finding_ids": [str(item.get("finding_id") or "") for item in matching],
            "code_slice": scenario.get("code_slice") or scenario.get("candidate"),
            "invariant_violated": lesson["invariant"],
            "suggested_repair": lesson["repair_pattern"],
            "required_regression": lesson["required_regression"],
            "confidence": float(lesson["confidence"]),
            "provenance": lesson["provenance"],
            "expected_finding_code": expected_code,
            "production_mutation": False,
            "automatic_fix": False,
            "automatic_commit": False,
            "automatic_push": False,
            "automatic_pull_request": False,
            "automatic_merge": False,
            "human_review_required": True,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        receipt["receipt_digest"] = _digest(receipt, size=16)
        receipts.append(receipt)
    packet = {
        "version": CRUCIBLE_REPLAY_VERSION,
        "registry_digest": loaded["registry_digest"],
        "scenario_count": len(receipts),
        "passed_count": sum(1 for item in receipts if item["finding_produced"]),
        "failed_count": sum(1 for item in receipts if not item["finding_produced"]),
        "receipts": receipts,
        "status": "PASSED" if receipts and all(item["finding_produced"] for item in receipts) else "FAILED",
        "production_mutation": False,
        "automatic_fix": False,
        "automatic_commit": False,
        "automatic_push": False,
        "automatic_pull_request": False,
        "automatic_merge": False,
        "human_review_required": True,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
    packet["packet_digest"] = _digest(packet, size=16)
    return packet


class ReviewLessonEngine:
    """Repository-bound typed lesson and external-review adapter."""

    def __init__(
        self,
        repo_root: str | Path = ".",
        *,
        registry_path: str | Path = DEFAULT_REGISTRY_PATH,
        learning_root: str | Path = DEFAULT_LEARNING_ROOT,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.registry_path = Path(registry_path)
        if not self.registry_path.is_absolute():
            self.registry_path = self.repo_root / self.registry_path
        self.learning_root = Path(learning_root).expanduser().resolve()
        self.findings_path = self.learning_root / "external_review_findings.jsonl"

    def summary(self) -> dict[str, Any]:
        registry = load_review_lesson_registry(self.registry_path)
        stored = 0
        if self.findings_path.exists():
            with self.findings_path.open("r", encoding="utf-8") as handle:
                stored = sum(1 for line in handle if line.strip())
        return {
            "version": REVIEW_LESSON_VERSION,
            "registry_path": str(self.registry_path),
            "registry_digest": registry["registry_digest"],
            "lesson_count": len(registry["lessons"]),
            "scenario_count": len(registry["scenarios"]),
            "detectors": sorted(DETECTORS),
            "stored_external_finding_count": stored,
            "truth_boundary": "review_learning_only",
            "production_mutation": False,
            "automatic_fix": False,
            "automatic_commit": False,
            "automatic_push": False,
            "automatic_pull_request": False,
            "automatic_merge": False,
            "human_review_required": True,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def normalize_review(
        self,
        payload: Mapping[str, Any],
        *,
        current_head: str = "",
    ) -> dict[str, Any]:
        head = current_head or _git_head(self.repo_root)
        return normalize_external_review(payload, current_head=head)

    def ingest_review(
        self,
        payload: Mapping[str, Any],
        *,
        current_head: str = "",
    ) -> dict[str, Any]:
        packet = self.normalize_review(payload, current_head=current_head)
        known: set[str] = set()
        if self.findings_path.exists():
            with self.findings_path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    finding_id = str(row.get("finding_id") or "")
                    if finding_id:
                        known.add(finding_id)
        stored: list[str] = []
        rejected: list[dict[str, str]] = []
        self.findings_path.parent.mkdir(parents=True, exist_ok=True)
        with self.findings_path.open("a", encoding="utf-8") as handle:
            for finding in packet["findings"]:
                finding_id = str(finding.get("finding_id") or "")
                if finding_id in known or finding.get("disposition") == "duplicate":
                    rejected.append({"finding_id": finding_id, "reason": "duplicate"})
                    continue
                handle.write(_canonical_json(finding) + "\n")
                known.add(finding_id)
                stored.append(finding_id)
        return {
            **packet,
            "status": "stored" if stored else "no_new_findings",
            "stored_count": len(stored),
            "stored_finding_ids": stored,
            "rejected": rejected,
        }

    def scan_source(self, *, file: str, source: str) -> dict[str, Any]:
        canonical_file = _safe_repo_path(file)
        if not canonical_file:
            raise ReviewLessonError("source scan file is required")
        findings = scan_source_for_review_lessons(file=canonical_file, source=source)
        packet = {
            "version": REVIEW_LESSON_VERSION,
            "file": canonical_file,
            "finding_count": len(findings),
            "findings": findings,
            "truth_boundary": "probable_static_review_lesson",
            "production_mutation": False,
            "automatic_fix": False,
            "automatic_commit": False,
            "automatic_push": False,
            "automatic_pull_request": False,
            "automatic_merge": False,
            "human_review_required": True,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        packet["packet_digest"] = _digest(packet, size=16)
        return packet

    def detector(self, detector_id: str, candidate: Any) -> dict[str, Any]:
        return run_review_detector(detector_id, candidate)

    def crucible(self, *, detector_ids: Sequence[str] = ()) -> dict[str, Any]:
        return run_crucible_replay(self.registry_path, detector_ids=detector_ids)

__all__ = [
    "CRUCIBLE_REPLAY_VERSION", "DEFAULT_LEARNING_ROOT", "DEFAULT_REGISTRY_PATH",
    "DETECTORS", "PATCH_AUTHORITY", "REGISTRY_VERSION", "REVIEW_FINDING_VERSION",
    "REVIEW_LESSON_VERSION", "VSA_PATCH_AUTHORITY", "ReviewLessonEngine",
    "ReviewLessonError", "detect_authority_aliases",
    "detect_count_without_byte_budget", "detect_implicit_coordinate_basis_change",
    "detect_nested_unit_double_application",
    "detect_noncanonical_interchange_acceptance", "detect_noncanonical_source_path",
    "detect_order_dependent_digesting", "detect_protected_metadata_overrides",
    "detect_schema_runtime_drift", "detect_stale_evidence_claim",
    "detect_truncate_before_sort", "detect_unwired_regression",
    "detect_uri_alias_encoding", "load_review_lesson_registry",
    "normalize_external_review", "run_crucible_replay", "run_review_detector",
    "scan_source_for_review_lessons", "validate_review_lesson_registry",
]
