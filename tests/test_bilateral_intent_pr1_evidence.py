"""Exact-head objective and Waboose evidence tests for bilateral intent PR1."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "598804b3dce8d39480d8494cf0144f872b01d9ca"
CANONICAL_INGESTION_BLOB = "84bd861cb36b12c07708d3de1b91cd7beccd1399"
OBJECTIVE = ROOT / ".aura/refactor_objectives/bilateral_intent_guardrail_foundry_pr1.v1.json"
REVISION = ROOT / ".aura/refactor_objectives/bilateral_intent_guardrail_foundry_pr1_revision.v1.json"
WABOOSE = ROOT / ".aura/waboose_requests/bilateral_intent_guardrail_foundry.v2.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _git_blob_sha(path: Path) -> str:
    payload = path.read_bytes()
    header = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header + payload).hexdigest()  # noqa: S324 - Git identity, not security


def test_objective_receipt_binds_exact_base_and_denies_authority():
    receipt = _load(OBJECTIVE)
    assert receipt["base_repository_head"] == BASE
    assert receipt["status"] == "PROPOSAL_ONLY"
    assert receipt["generated_artifact_disposition"] == "REGENERATE_FROM_FINAL_SOURCE_TREE_ONLY"
    assert receipt["candidate_head_bound_at_final_verification"] is True
    assert receipt["human_merge_decision_required"] is True
    authority = receipt["authority"]
    assert authority["human_confirmation_required"] is True
    assert all(authority[key] is False for key in (
        "memory_owner", "truth_owner", "policy_owner", "routing_owner",
        "verification_owner", "patch_authority", "production_mutation", "merge_authority",
    ))


def test_recorded_candidate_source_blobs_match_checkout():
    receipt = _load(OBJECTIVE)
    for relative_path, expected_blob in receipt["candidate_source_blobs"].items():
        assert _git_blob_sha(ROOT / relative_path) == expected_blob


def test_objective_scope_separates_source_from_generated_navigation():
    receipt = _load(OBJECTIVE)
    source = set(receipt["allowed_source_and_evidence_paths"])
    generated = set(receipt["generated_navigation_paths"])
    assert source.isdisjoint(generated)
    assert generated == {".aura/CODEMAP.json", ".aura/CODEMAP.md", "topology_map.json"}
    assert "aura_bilateral_intent_ingestion.py" in source
    assert "aura_intent_ingestion_core.py" not in source
    assert receipt["transport_boundary"]["request_triggered_export_is_authoritative_forensic_evidence"] is False


def test_canonical_ingestion_is_exact_and_duplicate_core_is_absent():
    canonical = ROOT / "aura_intent_ingestion.py"
    duplicate = ROOT / "aura_intent_ingestion_core.py"
    assert _git_blob_sha(canonical) == CANONICAL_INGESTION_BLOB
    assert not duplicate.exists()
    receipt = _load(OBJECTIVE)
    decision = receipt["structural_decision"]
    assert decision["canonical_ingestion_file_changed"] is False
    assert decision["duplicate_legacy_core_allowed"] is False
    assert decision["monkeypatching_allowed"] is False
    assert decision["companion_is_authority_owner"] is False
    assert decision["canonical_route_recomputed_by_companion"] is False


def test_revision_receipt_records_bounded_restructure_without_drift():
    revision = _load(REVISION)
    assert revision["base_repository_head"] == BASE
    assert revision["revision_class"] == "BOUNDED_PLAN_RESTRUCTURING"
    assert revision["requires_council_replan"] is True
    assert revision["current_reproof_required"] is True
    assert revision["intent_changed"] is False
    assert revision["negative_requirements_changed"] is False
    assert revision["guardrails_changed"] is False
    assert revision["scope_changed"] is False
    assert revision["authority_changed"] is False
    assert revision["revised_structure"]["duplicated_legacy_core"] is None
    assert revision["revised_structure"]["monkeypatching"] is False


def test_waboose_profile_preserves_required_invariants_and_risks():
    request = _load(WABOOSE)
    assert request["base_repository_head"] == BASE
    assert request["objective_receipt"] == OBJECTIVE.relative_to(ROOT).as_posix()
    assert request["revision_receipt"] == REVISION.relative_to(ROOT).as_posix()
    invariants = set(request["invariants"])
    risks = set(request["risk_map"])
    for required in (
        "negative requirements are never discarded by compression",
        "aura_intent_ingestion remains the canonical ingestion owner",
        "the bilateral companion does not monkeypatch the canonical owner",
        "the canonical ingestion implementation is not duplicated",
        "no self-verification",
        "no production mutation",
        "no partial candidate bundle is published",
    ):
        assert required in invariants
    for required in (
        "negation lost in compression",
        "stale confirmation replay",
        "silent plan drift",
        "duplicate ingestion implementation",
        "monkeypatch coupling",
        "generated CODEMAP drift",
    ):
        assert required in risks
    assert request["review_scope"]["canonical_unchanged_paths"]["aura_intent_ingestion.py"] == CANONICAL_INGESTION_BLOB
    assert request["review_scope"]["forbidden_paths"] == ["aura_intent_ingestion_core.py"]
    assert all(value is False for key, value in request["authority"].items() if key != "review_only")
    assert request["authority"]["review_only"] is True
