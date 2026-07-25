"""Exact-scope evidence for the Bilateral Intent PR 2 slice."""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OBJECTIVE = (
    REPO_ROOT
    / ".aura"
    / "refactor_objectives"
    / "bilateral_intent_guardrail_foundry_pr2.v1.json"
)
REVISION = (
    REPO_ROOT
    / ".aura"
    / "refactor_objectives"
    / "bilateral_intent_guardrail_foundry_pr2_revision.v1.json"
)
WABOOSE = (
    REPO_ROOT
    / ".aura"
    / "waboose_requests"
    / "bilateral_intent_guardrail_foundry_pr2.v1.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_pr2_objective_is_exact_head_bounded_and_proposal_only():
    objective = _load(OBJECTIVE)
    assert objective["base_repository_head"] == "2cf38f12e42848f6b3ce3bd8b24cee86a9cde02d"
    assert objective["slice"] == "PR2_CANONICAL_INTEGRATION_AND_GATE_DIALOGUE"
    assert objective["authority"]["merge"] is False
    assert objective["authority"]["production_mutation"] is False
    assert objective["authority"]["learning_promotion"] is False
    assert "aura_unified_memory_continuity.py" in objective["preserved_canonical_owners"]
    assert "aura_unified_memory_continuity_toolchain.py" in objective["preserved_canonical_owners"]


def test_plan_revision_records_endpoint_reuse_without_shadow_owner():
    revision = _load(REVISION)
    assert revision["discovery"] == "existing_gate_address_and_approval_routes_are_canonical"
    assert revision["invalidated_assumption"] == "new_server_route_owner_required"
    assert revision["replacement"] == "separate_service_actions_over_existing_routes"
    assert revision["new_authority"] is False
    assert revision["human_reconfirmation_required"] is False
    assert revision["merge_authority"] is False


def test_waboose_request_covers_bilateral_impact_and_negative_proof():
    request = _load(WABOOSE)
    assert "positive_requirement_proof" in request["required_checks"]
    assert "negative_requirement_proof" in request["required_checks"]
    assert "hard_guardrail_non_removability" in request["required_checks"]
    assert "confirmation_staleness" in request["required_checks"]
    assert "canonical_owner_reuse" in request["required_checks"]
    assert request["external_reviewers_authorized"] == ["CodeRabbit_after_all_internal_proof"]


def test_pr2_companion_declares_reference_only_authority():
    from aura_bilateral_intent_canonical import canonical_binding_capabilities

    packet = canonical_binding_capabilities()
    assert packet["compiles_intent_packet"] is True
    assert packet["compiles_semantic_ledger"] is True
    assert packet["compiles_arena_evidence_slice"] is True
    assert packet["act_capsule_envelope_optional_until_plan_exists"] is True
    assert packet["unified_execution_binding_reference_only"] is True
    assert packet["u7_reference_only"] is True
    assert packet["authority"]["automatic_merge"] is False
    assert packet["authority"]["production_mutation"] is False


def test_pr2_does_not_monkeypatch_canonical_owners():
    source = (REPO_ROOT / "aura_bilateral_intent_canonical.py").read_text(
        encoding="utf-8"
    )
    forbidden = (
        "setattr(aura_unified_memory_continuity",
        "sys.modules[",
        "monkeypatch",
        "production_mutation = True",
        "automatic_merge = True",
    )
    assert all(token not in source for token in forbidden)
