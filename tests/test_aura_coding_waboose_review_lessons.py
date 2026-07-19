from __future__ import annotations

import json
from pathlib import Path

import pytest

from aura_coding_waboose_review_lessons import (
    DETECTORS,
    ReviewLessonEngine,
    ReviewLessonError,
    load_review_lesson_registry,
    normalize_external_review,
    run_crucible_replay,
    run_review_detector,
    scan_source_for_review_lessons,
    validate_review_lesson_registry,
)

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / ".aura" / "review_lessons" / "pr164_spatial_review_lessons.json"


def test_registry_runtime_validation_and_crucible_replay() -> None:
    registry = load_review_lesson_registry(REGISTRY)
    assert len(registry["lessons"]) == 13
    assert len(registry["scenarios"]) == 13
    assert {item["detector_id"] for item in registry["lessons"]} == set(DETECTORS)

    replay = run_crucible_replay(REGISTRY)
    assert replay["status"] == "PASSED"
    assert replay["passed_count"] == 13
    assert replay["failed_count"] == 0
    assert replay["automatic_merge"] is False
    assert replay["human_review_required"] is True
    assert all(item["receipt_digest"] for item in replay["receipts"])


def test_registry_rejects_unknown_detector_and_digest_drift() -> None:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    registry["lessons"][0]["detector_id"] = "detect_missing"
    registry.pop("registry_digest")
    with pytest.raises(ReviewLessonError, match="unknown detector"):
        validate_review_lesson_registry(registry)

    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    registry["lessons"][0]["invariant"] += " changed"
    with pytest.raises(ReviewLessonError, match="digest mismatch"):
        validate_review_lesson_registry(registry)


def test_registry_runtime_matches_schema_authority_and_canonical_order() -> None:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    registry["authority"]["automatic_merge"] = True
    registry.pop("registry_digest")
    with pytest.raises(ReviewLessonError, match="authority envelope"):
        validate_review_lesson_registry(registry)

    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    registry["lessons"] = list(reversed(registry["lessons"]))
    registry.pop("registry_digest")
    with pytest.raises(ReviewLessonError, match="canonically sorted"):
        validate_review_lesson_registry(registry)


def test_external_review_flags_are_strict_booleans() -> None:
    with pytest.raises(ReviewLessonError, match="is_outdated must be a boolean"):
        normalize_external_review(
            {
                "review_threads": [
                    {
                        "path": "module.py",
                        "line": 1,
                        "is_outdated": "false",
                        "comments": [{"author": "Codex", "body": "test"}],
                    }
                ]
            }
        )


def test_authority_detectors_are_recursive_and_separator_insensitive() -> None:
    aliases = run_review_detector(
        "detect_authority_aliases",
        {"metadata": {"automaticMerge": True, "nested": {"p-at-ch Auth_ority": True}}},
    )
    assert aliases["finding_count"] == 2
    assert {f["code"] for f in aliases["findings"]} == {"AUTHORITY_ALIAS"}

    overrides = run_review_detector(
        "detect_protected_metadata_overrides",
        {"metadata": {"automatic_merge": True, "automatic_push": None}},
    )
    assert overrides["finding_count"] == 2
    assert all(f["repair_authority"] is False for f in overrides["findings"])


def test_canonical_path_and_uri_detectors_fail_closed() -> None:
    paths = run_review_detector(
        "detect_noncanonical_source_path",
        {"paths": ["./module.py", "pkg/./module.py", "../outside.py", "/etc/passwd"]},
    )
    assert paths["finding_count"] == 4

    safe = run_review_detector(
        "detect_noncanonical_source_path",
        {"paths": ["pkg/module.py", "pkg/file.name.py"]},
    )
    assert safe["finding_count"] == 0

    uris = run_review_detector(
        "detect_uri_alias_encoding",
        {"uris": ["aura://coding/%2fetc", "https://host//path", "https://u:p@host/path?q=1#x"]},
    )
    assert uris["finding_count"] == 3


def test_boundedness_schema_workflow_and_evidence_detectors() -> None:
    count = run_review_detector(
        "detect_count_without_byte_budget",
        {"max_record_count": 20, "attacker_controlled": True},
    )
    assert count["finding_count"] == 1

    bounded = run_review_detector(
        "detect_count_without_byte_budget",
        {"max_record_count": 20, "max_record_bytes": 2048, "attacker_controlled": True},
    )
    assert bounded["finding_count"] == 0

    drift = run_review_detector(
        "detect_schema_runtime_drift",
        {"schema_accepts": True, "runtime_accepts": False, "invariant": "positive scale"},
    )
    assert drift["finding_count"] == 1

    unwired = run_review_detector(
        "detect_unwired_regression",
        {
            "test_path": "tests/test_new_regression.py",
            "workflow": (
                "python -m py_compile module.py\n"
                "ruff check module.py\n"
                "pytest tests/test_other.py\n"
            ),
        },
    )
    assert unwired["finding_count"] == 1
    assert set(unwired["findings"][0]["evidence"]["missing_stages"]) == {
        "py_compile", "ruff", "pytest"
    }

    stale = run_review_detector(
        "detect_stale_evidence_claim",
        {
            "claim": "current-head workflow passed",
            "evidence_status": "configured",
            "evidence_head": "a" * 40,
            "current_head": "b" * 40,
        },
    )
    assert stale["finding_count"] == 1


def test_determinism_coordinate_and_interchange_detectors() -> None:
    assert run_review_detector(
        "detect_order_dependent_digesting",
        {"collection_name": "links", "canonicalized_before_digest": False},
    )["finding_count"] == 1
    assert run_review_detector(
        "detect_truncate_before_sort",
        {"collection": "links", "truncated_before_sort": True},
    )["finding_count"] == 1
    assert run_review_detector(
        "detect_implicit_coordinate_basis_change",
        {
            "parent": {"handedness": "RIGHT", "up_axis": "Y"},
            "child": {"handedness": "LEFT", "up_axis": "Z"},
            "explicit_conversion": False,
        },
    )["finding_count"] == 1
    assert run_review_detector(
        "detect_nested_unit_double_application",
        {
            "parent_unit_scale": 0.01,
            "child_unit_scale": 0.01,
            "translation_converted_to_meters": True,
            "accumulated_scale_includes_unit": True,
        },
    )["finding_count"] == 1
    assert run_review_detector(
        "detect_noncanonical_interchange_acceptance",
        {
            "accepted": True,
            "records": [{"id": "b"}, {"id": "a"}, {"id": "a"}],
            "set_like_values": ["z", "a", "a"],
        },
    )["finding_count"] == 1


def test_external_review_normalization_distinguishes_review_kinds_and_dispositions() -> None:
    head = "a" * 40
    payload = {
        "head_sha": head,
        "current_head": head,
        "pr_number": 164,
        "comments": [{"id": 1, "author": {"login": "coderabbitai[bot]"}, "body": "Review summary only."}],
        "review_threads": [
            {
                "path": "module.py",
                "line": 10,
                "is_outdated": True,
                "comments": [
                    {"id": 2, "author": {"login": "chatgpt-codex-connector"}, "body": "Canonicalize links before applying the projection cap."},
                    {"id": 3, "author": {"login": "chatgpt-codex-connector"}, "body": "Canonicalize links before applying the projection cap."},
                ],
            }
        ],
        "reviews": [
            {"id": 4, "author": {"login": "coderabbitai"}, "body": "Review completed.", "resolved": True}
        ],
    }
    packet = normalize_external_review(payload)
    assert packet["finding_count"] == 4
    assert {item["review_kind"] for item in packet["findings"]} == {
        "top_level_pr_comment", "inline_review_thread", "review_submission"
    }
    inline = [item for item in packet["findings"] if item["review_kind"] == "inline_review_thread"]
    assert inline[0]["reviewer"] == "Codex"
    assert inline[0]["disposition"] == "outdated"
    assert inline[1]["disposition"] == "duplicate"
    assert packet["automatic_merge"] is False


def test_review_lesson_engine_stores_deduplicated_findings(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    registry_path = repo / ".aura" / "review_lessons" / REGISTRY.name
    registry_path.parent.mkdir(parents=True)
    registry_path.write_text(REGISTRY.read_text(encoding="utf-8"), encoding="utf-8")
    engine = ReviewLessonEngine(repo, registry_path=registry_path, learning_root=tmp_path / "learning")
    payload = {
        "head_sha": "a" * 40,
        "current_head": "a" * 40,
        "pr_number": 164,
        "findings": [
            {
                "id": "f1", "author": "CodeRabbit", "file": "module.py", "line": 1,
                "body": "Enforce a byte cap for interaction evidence."
            }
        ],
    }
    first = engine.ingest_review(payload, current_head="a" * 40)
    second = engine.ingest_review(payload, current_head="a" * 40)
    assert first["stored_count"] == 1
    assert second["stored_count"] == 0
    assert engine.summary()["stored_external_finding_count"] == 1


def test_source_scan_recognizes_narrow_pr164_shapes() -> None:
    source = '''
MAX_LINK_COUNT = 20

def compile_packet(metadata, links):
    packet = {
        "automatic_merge": False,
        **metadata,
    }
    bounded = links[:MAX_LINK_COUNT]
    bounded = sorted(bounded)
    return packet, bounded
'''
    findings = scan_source_for_review_lessons(file="module.py", source=source)
    codes = {item["code"] for item in findings}
    assert "PROTECTED_AUTHORITY_OVERRIDE_SHAPE" in codes
    assert "TRUNCATE_BEFORE_SORT_SHAPE" in codes
    assert "COUNT_ONLY_BOUND_SHAPE" in codes
    assert all(item["source_grounded"] is True for item in findings)
    assert all(item["repair_authority"] is False for item in findings)


def test_payload_and_path_byte_bounds_fail_closed() -> None:
    with pytest.raises(ReviewLessonError, match="exceeds"):
        normalize_external_review({"comments": [{"body": "x" * 1_100_000}]})

    with pytest.raises(ReviewLessonError, match="path exceeds"):
        normalize_external_review(
            {"findings": [{"author": "Codex", "file": "a" * 1100, "body": "test"}]}
        )
