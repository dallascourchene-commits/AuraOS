"""Detector dispatch and Crucible replay over validated review lessons."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from aura_review_lessons_contracts import (
    _MAX_SCENARIO_BYTES,
    CRUCIBLE_REPLAY_VERSION,
    DEFAULT_REGISTRY_PATH,
    PATCH_AUTHORITY,
    REVIEW_LESSON_VERSION,
    VSA_PATCH_AUTHORITY,
    ReviewLessonError,
    _bounded_json,
    _digest,
)
from aura_review_lessons_registry import (
    DETECTORS,
    load_review_lesson_registry,
    validate_review_lesson_registry,
)


def _authority_envelope() -> dict[str, Any]:
    return {
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


def run_review_detector(detector_id: str, candidate: Any) -> dict[str, Any]:
    """Run one bounded deterministic detector and return a review-only packet."""

    detector = DETECTORS.get(detector_id)
    if detector is None:
        raise ReviewLessonError(f"unknown review detector: {detector_id}")
    _bounded_json(
        candidate,
        maximum=_MAX_SCENARIO_BYTES,
        label="review detector candidate",
    )
    findings = detector(candidate)
    packet = {
        "version": REVIEW_LESSON_VERSION,
        "detector_id": detector_id,
        "finding_count": len(findings),
        "findings": findings,
        "truth_boundary": "review_hypothesis_only",
        **_authority_envelope(),
    }
    packet["packet_digest"] = _digest(packet, size=16)
    return packet


def _registry(value: str | Path | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return validate_review_lesson_registry(value)
    return load_review_lesson_registry(value)


def _selected_detector_ids(
    requested: Sequence[str],
    *,
    available: set[str],
) -> tuple[str, ...]:
    if isinstance(requested, (str, bytes, bytearray)):
        raise ReviewLessonError("detector_ids must be a sequence of detector IDs")
    selected = tuple(
        dict.fromkeys(
            str(item).strip() for item in requested if str(item).strip()
        )
    )
    unknown = sorted(set(selected) - available)
    if unknown:
        raise ReviewLessonError(f"unknown selected review detectors: {unknown}")
    return selected


def run_crucible_replay(
    registry_path: str | Path | Mapping[str, Any] = DEFAULT_REGISTRY_PATH,
    *,
    detector_ids: Sequence[str] = (),
) -> dict[str, Any]:
    """Replay registered adversarial scenarios and emit proof-oriented receipts."""

    registry = _registry(registry_path)
    lessons = {
        str(item["detector_id"]): dict(item)
        for item in registry["lessons"]
        if isinstance(item, Mapping)
    }
    selected = _selected_detector_ids(detector_ids, available=set(lessons))
    selected_set = set(selected)

    receipts: list[dict[str, Any]] = []
    for raw_scenario in registry["scenarios"]:
        scenario = dict(raw_scenario)
        detector_id = str(scenario["detector_id"])
        if selected_set and detector_id not in selected_set:
            continue
        lesson = lessons.get(detector_id)
        if lesson is None:
            raise ReviewLessonError(
                f"review scenario has no matching lesson: {detector_id}"
            )
        result = run_review_detector(detector_id, scenario["candidate"])
        expected_code = str(scenario["expected_finding_code"])
        matching = [
            item
            for item in result["findings"]
            if isinstance(item, Mapping)
            and str(item.get("code")) == expected_code
        ]
        finding_produced = bool(matching)
        receipt = {
            "version": CRUCIBLE_REPLAY_VERSION,
            "scenario_id": str(scenario["scenario_id"]),
            "detector_id": detector_id,
            "expected_finding_code": expected_code,
            "finding_produced": finding_produced,
            "finding_count": int(result["finding_count"]),
            "finding_ids": sorted(
                str(item.get("finding_id") or "")
                for item in matching
                if str(item.get("finding_id") or "")
            ),
            "code_slice": str(scenario["code_slice"]),
            "invariant_violated": (
                str(lesson["invariant"]) if finding_produced else ""
            ),
            "suggested_repair": str(lesson["repair_pattern"]),
            "required_regression": str(lesson["required_regression"]),
            "confidence": float(lesson["confidence"]),
            "provenance": dict(lesson["provenance"]),
            **_authority_envelope(),
        }
        _bounded_json(
            receipt,
            maximum=_MAX_SCENARIO_BYTES,
            label=f"review replay receipt {receipt['scenario_id']}",
        )
        receipt["receipt_digest"] = _digest(receipt, size=16)
        receipts.append(receipt)

    receipts.sort(key=lambda item: str(item["scenario_id"]))
    passed_count = sum(1 for item in receipts if item["finding_produced"])
    failed_count = len(receipts) - passed_count
    packet = {
        "version": CRUCIBLE_REPLAY_VERSION,
        "registry_digest": str(registry["registry_digest"]),
        "selected_detector_ids": list(selected),
        "scenario_count": len(receipts),
        "passed_count": passed_count,
        "failed_count": failed_count,
        "receipts": receipts,
        "status": "PASSED" if failed_count == 0 else "FAILED",
        **_authority_envelope(),
    }
    packet["packet_digest"] = _digest(packet, size=16)
    return packet


__all__ = ["run_crucible_replay", "run_review_detector"]
