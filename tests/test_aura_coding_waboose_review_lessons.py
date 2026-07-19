from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from aura_coding_waboose_review_lessons import (
    DETECTORS,
    PATCH_AUTHORITY,
    ReviewLessonEngine,
    ReviewLessonError,
    detect_authority_aliases,
    detect_count_without_byte_budget,
    detect_implicit_coordinate_basis_change,
    detect_nested_unit_double_application,
    detect_noncanonical_interchange_acceptance,
    detect_noncanonical_source_path,
    detect_order_dependent_digesting,
    detect_protected_metadata_overrides,
    detect_schema_runtime_drift,
    detect_stale_evidence_claim,
    detect_truncate_before_sort,
    detect_unwired_regression,
    detect_uri_alias_encoding,
    load_review_lesson_registry,
    normalize_external_review,
    run_crucible_replay,
    validate_review_lesson_registry,
)

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / ".aura" / "review_lessons" / "pr164_spatial_review_lessons.json"
SCHEMA = ROOT / "schemas" / "aura_review_lesson.schema.json"


def test_registry_schema_runtime_and_digest_are_aligned() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(payload)
    validated = validate_review_lesson_registry(payload)

    assert validated["registry_digest"] == payload["registry_digest"]
    assert len(validated["lessons"]) == 13
    assert len(validated["scenarios"]) == 13
    assert {item["detector_id"] for item in validated["lessons"]} == set(DETECTORS)
    assert validated["authority"]["automatic_merge"] is False
    assert validated["authority"]["patch_authority"] == PATCH_AUTHORITY


def test_registry_rejects_digest_tampering_and_duplicate_identities() -> None:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    tampered = copy.deepcopy(payload)
    tampered["lessons"][0]["invariant"] = "weakened"
    with pytest.raises(ReviewLessonError, match="digest mismatch"):
        validate_review_lesson_registry(tampered)

    duplicate = copy.deepcopy(payload)
    duplicate.pop("registry_digest")
    duplicate["lessons"][1]["lesson_id"] = duplicate["lessons"][0]["lesson_id"]
    with pytest.raises(ReviewLessonError, match="unique"):
        validate_review_lesson_registry(duplicate)


def test_crucible_replays_every_pr164_lesson_with_typed_receipts() -> None:
    result = run_crucible_replay(REGISTRY)

    assert result["status"] == "PASSED"
    assert result["scenario_count"] == 13
    assert result["passed_count"] == 13
    assert result["failed_count"] == 0
    assert all(item["finding_produced"] for item in result["receipts"])
    assert all(item["invariant_violated"] for item in result["receipts"])
    assert all(item["required_regression"] for item in result["receipts"])
    assert all(item["automatic_merge"] is False for item in result["receipts"])


def test_authority_detectors_normalize_case_and_separators_recursively() -> None:
    candidate = {
        "automaticMerge": True,
        "nested": {
            "pAtch-Authority": True,
            "automatic_merge": True,
            "safe_label": "visible",
        },
    }

    aliases = detect_authority_aliases(candidate)
    overrides = detect_protected_metadata_overrides(candidate)

    assert {item["code"] for item in aliases} == {"AUTHORITY_ALIAS"}
    assert len(aliases) == 2
    assert len(overrides) == 1
    assert overrides[0]["evidence"]["key"] == "automatic_merge"
    assert all(item["repair_authority"] is False for item in aliases + overrides)


def test_path_and_uri_detectors_reject_aliases_but_allow_canonical_values() -> None:
    bad_paths = detect_noncanonical_source_path(
        ["./module.py", "pkg/./module.py", "../../outside.py", "/etc/passwd", "pkg\\module.py"]
    )
    assert len(bad_paths) == 5
    assert detect_noncanonical_source_path("pkg/module.py") == []

    bad_uris = detect_uri_alias_encoding(
        ["aura://coding/%2fetc", "https://host//path", "https://user:pass@host/path?x=1#y"]
    )
    assert len(bad_uris) == 3
    assert detect_uri_alias_encoding("https://host/path%20with%20space") == []


def test_determinism_and_bounds_detectors_cover_pr164_failure_shapes() -> None:
    assert detect_order_dependent_digesting(
        {"collection_name": "links", "canonicalized_before_digest": False}
    )[0]["code"] == "ORDER_DEPENDENT_DIGEST"
    assert detect_truncate_before_sort(
        {"truncated_before_sort": True, "collection": "links"}
    )[0]["code"] == "TRUNCATE_BEFORE_SORT"
    assert detect_count_without_byte_budget(
        {"max_source_ref_count": 32, "attacker_controlled": True}
    )[0]["code"] == "COUNT_ONLY_BOUND"
    assert detect_count_without_byte_budget(
        {"max_source_ref_count": 32, "max_source_ref_bytes": 4096, "attacker_controlled": True}
    ) == []
    assert detect_noncanonical_interchange_acceptance(
        {"accepted": True, "records": [{"id": "b"}, {"id": "a"}, {"id": "a"}]}
    )[0]["code"] == "NONCANONICAL_INTERCHANGE_ACCEPTED"


def test_coordinate_schema_workflow_and_evidence_detectors() -> None:
    assert detect_implicit_coordinate_basis_change(
        {
            "parent": {"handedness": "RIGHT", "up_axis": "Y"},
            "child": {"handedness": "LEFT", "up_axis": "Z"},
            "explicit_conversion": False,
        }
    )[0]["code"] == "IMPLICIT_BASIS_CHANGE"
    assert detect_nested_unit_double_application(
        {
            "parent_unit_scale": 0.01,
            "child_unit_scale": 0.01,
            "translation_converted_to_meters": True,
            "accumulated_scale_includes_unit": True,
        }
    )[0]["code"] == "NESTED_UNIT_DOUBLE_APPLICATION"
    assert detect_schema_runtime_drift(
        {"schema_accepts": True, "runtime_accepts": False, "invariant": "positive scale"}
    )[0]["code"] == "SCHEMA_RUNTIME_DRIFT"
    assert detect_unwired_regression(
        {
            "test_path": "tests/test_final.py",
            "workflow": "python -m py_compile module.py\nruff check module.py\npytest tests/test_other.py\n",
        }
    )[0]["code"] == "UNWIRED_REGRESSION"
    assert detect_stale_evidence_claim(
        {
            "claim": "current workflow passed",
            "evidence_status": "configured",
            "evidence_head": "a",
            "current_head": "b",
        }
    )[0]["code"] == "STALE_EVIDENCE_CLAIM"


def test_external_review_adapter_separates_current_historical_resolved_outdated_and_duplicate() -> None:
    payload = {
        "head_sha": "a" * 40,
        "pr_number": 164,
        "comments": [
            {
                "id": 1,
                "author": {"login": "coderabbitai[bot]"},
                "body": "Schema/runtime drift permits zero scale.",
                "path": "schema.json",
                "line": 10,
            },
            {
                "id": 2,
                "author": {"login": "coderabbitai[bot]"},
                "body": "Schema/runtime drift permits zero scale.",
                "path": "schema.json",
                "line": 10,
            },
        ],
        "review_threads": [
            {
                "path": "scene.py",
                "line": 22,
                "is_resolved": True,
                "comments": [
                    {
                        "id": 3,
                        "author": {"login": "chatgpt-codex-connector"},
                        "body": "Canonical ordering must be checked before digest acceptance.",
                    }
                ],
            },
            {
                "path": "asset.py",
                "line": 33,
                "is_outdated": True,
                "comments": [
                    {
                        "id": 4,
                        "author": {"login": "chatgpt-codex-connector"},
                        "body": "Reject encoded separators in asset URIs.",
                    }
                ],
            },
        ],
        "reviews": [
            {
                "id": 5,
                "author": {"login": "human-reviewer"},
                "body": "Manual review submission.",
            }
        ],
    }

    result = normalize_external_review(payload, current_head="b" * 40)
    dispositions = [item["disposition"] for item in result["findings"]]

    assert result["finding_count"] == 5
    assert "historical" in dispositions
    assert "duplicate" in dispositions
    assert "resolved" in dispositions
    assert "outdated" in dispositions
    assert {item["reviewer"] for item in result["findings"]} >= {"CodeRabbit", "Codex"}
    assert all(item["automatic_pull_request"] is False for item in result["findings"])


def test_review_lesson_engine_ingests_append_only_without_duplicate_storage(tmp_path: Path) -> None:
    engine = ReviewLessonEngine(
        ROOT,
        registry_path=REGISTRY,
        learning_root=tmp_path / "learning",
    )
    payload = {
        "head_sha": "a" * 40,
        "pr_number": 164,
        "findings": [
            {
                "id": "f-1",
                "author": "CodeRabbit",
                "file": "module.py",
                "line": 2,
                "title": "Reject authority aliases",
                "message": "automaticMerge bypasses the authority boundary.",
            }
        ],
    }

    first = engine.ingest_review(payload, current_head="a" * 40)
    second = engine.ingest_review(payload, current_head="a" * 40)

    assert first["stored_count"] == 1
    assert second["stored_count"] == 0
    assert engine.summary()["stored_external_finding_count"] == 1


def test_review_payload_and_detector_candidates_are_byte_bounded() -> None:
    with pytest.raises(ReviewLessonError, match="review payload exceeds"):
        normalize_external_review({"comments": [{"body": "x" * 1_100_000}]})

    registry = load_review_lesson_registry(REGISTRY)
    assert registry["truth_boundary"] == "review_learning_only"
