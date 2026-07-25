"""Exact-head objective and Waboose evidence tests for bilateral intent PR1."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "598804b3dce8d39480d8494cf0144f872b01d9ca"
OBJECTIVE = ROOT / ".aura/refactor_objectives/bilateral_intent_guardrail_foundry_pr1.v1.json"
WABOOSE = ROOT / ".aura/waboose_requests/bilateral_intent_guardrail_foundry.v2.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


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


def test_objective_scope_separates_source_from_generated_navigation():
    receipt = _load(OBJECTIVE)
    source = set(receipt["allowed_source_and_evidence_paths"])
    generated = set(receipt["generated_navigation_paths"])
    assert source.isdisjoint(generated)
    assert generated == {".aura/CODEMAP.json", ".aura/CODEMAP.md", "topology_map.json"}
    assert receipt["transport_boundary"]["request_triggered_export_is_authoritative_forensic_evidence"] is False


def test_waboose_profile_preserves_required_invariants_and_risks():
    request = _load(WABOOSE)
    assert request["base_repository_head"] == BASE
    assert request["objective_receipt"] == OBJECTIVE.relative_to(ROOT).as_posix()
    invariants = set(request["invariants"])
    risks = set(request["risk_map"])
    for required in (
        "negative requirements are never discarded by compression",
        "no self-verification",
        "no production mutation",
        "no partial candidate bundle is published",
    ):
        assert required in invariants
    for required in (
        "negation lost in compression",
        "stale confirmation replay",
        "silent plan drift",
        "generated CODEMAP drift",
    ):
        assert required in risks
    assert all(value is False for key, value in request["authority"].items() if key != "review_only")
    assert request["authority"]["review_only"] is True
