"""Detector dispatch and Crucible replay over validated review lessons."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
import re
import subprocess
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

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_REPOSITORY_ROOT = Path(__file__).resolve().parent


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
        sorted({str(item).strip() for item in requested if str(item).strip()})
    )
    unknown = sorted(set(selected) - available)
    if unknown:
        raise ReviewLessonError(f"unknown selected review detectors: {unknown}")
    return selected


def _git(
    repository_root: Path,
    *arguments: str,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repository_root), *arguments],
        check=check,
        capture_output=True,
        text=True,
        timeout=20,
    )


def _repository_evidence(
    repository_root: Path,
    *,
    expected_repository_head: str | None,
) -> dict[str, str]:
    try:
        top_level = Path(
            _git(repository_root, "rev-parse", "--show-toplevel").stdout.strip()
        ).resolve()
        root = repository_root.resolve()
        if top_level != root:
            raise ReviewLessonError(
                "review replay root must be the checked-out repository root"
            )
        head = _git(root, "rev-parse", "HEAD").stdout.strip().lower()
        tree = _git(root, "rev-parse", "HEAD^{tree}").stdout.strip().lower()
    except (OSError, subprocess.SubprocessError) as exc:
        raise ReviewLessonError(
            f"exact repository evidence is unavailable: {exc}"
        ) from exc
    if not _SHA_RE.fullmatch(head) or not _SHA_RE.fullmatch(tree):
        raise ReviewLessonError("Git returned malformed repository evidence")
    if expected_repository_head is not None:
        expected = str(expected_repository_head).strip().lower()
        if not _SHA_RE.fullmatch(expected):
            raise ReviewLessonError(
                "expected_repository_head must be a lowercase 40-character SHA"
            )
        if head != expected:
            raise ReviewLessonError(
                f"checked-out repository head {head} does not match expected {expected}"
            )
    return {"repository_head": head, "repository_tree": tree}


def _registry_merge_is_ancestor(
    repository_root: Path,
    *,
    merge_commit: str,
    repository_head: str,
) -> bool:
    if repository_head == merge_commit:
        return True
    result = _git(
        repository_root,
        "merge-base",
        "--is-ancestor",
        merge_commit,
        repository_head,
        check=False,
    )
    return result.returncode == 0


def _validate_registry_freshness(
    registry: Mapping[str, Any],
    *,
    repository_root: Path,
    evidence: Mapping[str, str],
) -> None:
    current_head = str(evidence["repository_head"])
    merge_commit = str(registry["merge_commit"])
    if current_head == merge_commit:
        return
    if not _registry_merge_is_ancestor(
        repository_root,
        merge_commit=merge_commit,
        repository_head=current_head,
    ):
        raise ReviewLessonError(
            "review lesson registry is stale for the checked-out repository head: "
            f"registry merge {merge_commit}, current head {current_head}"
        )


def run_crucible_replay(
    registry_path: str | Path | Mapping[str, Any] = DEFAULT_REGISTRY_PATH,
    *,
    detector_ids: Sequence[str] = (),
    repository_root: str | Path = _REPOSITORY_ROOT,
    expected_repository_head: str | None = None,
) -> dict[str, Any]:
    """Replay registered scenarios with exact-head and ancestry-bound evidence."""

    registry = _registry(registry_path)
    root = Path(repository_root).resolve()
    evidence = _repository_evidence(
        root,
        expected_repository_head=expected_repository_head,
    )
    _validate_registry_freshness(
        registry,
        repository_root=root,
        evidence=evidence,
    )
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
    if not receipts:
        raise ReviewLessonError("crucible replay selected zero scenarios")
    required_detector_ids = selected_set or set(lessons)
    exercised_detector_ids = {
        str(item["detector_id"])
        for item in receipts
    }
    missing_detector_ids = sorted(required_detector_ids - exercised_detector_ids)
    if missing_detector_ids:
        raise ReviewLessonError(
            "crucible replay is missing scenario coverage for detectors: "
            f"{missing_detector_ids}"
        )
    passed_count = sum(1 for item in receipts if item["finding_produced"])
    failed_count = len(receipts) - passed_count
    packet = {
        "version": CRUCIBLE_REPLAY_VERSION,
        "registry_digest": str(registry["registry_digest"]),
        "registry_repository_head": str(registry["repository_head"]),
        "registry_merge_commit": str(registry["merge_commit"]),
        "repository_head": evidence["repository_head"],
        "repository_tree": evidence["repository_tree"],
        "registry_ancestry_verified": True,
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
