from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest
import jsonschema

from aura_agent_arena_mcp import TOOL_DEFINITIONS, handle_request
from aura_agent_arena_persistence_bridge import PersistentAuraAgentArenaBridge
from aura_agent_ir_compiler import AgentIRCompiler
from aura_architect_council_v3 import route_compass_failure_classes
from aura_arena_experience_ledger import ArenaExperienceLedger
from aura_change_graph import (
    build_compass_change_graph,
    compile_compass_act_capsules,
    validate_compass_change_graph,
)
from aura_coding_relationship_compass import CompassRolloutMode, validate_compass_rollout
from aura_emergent_potential_repl import discover_bounded_emergent_candidates
from aura_emergent_result_verifier import verify_bounded_emergent_discovery
from aura_event_contracts import stable_digest
from aura_qdkt_observations import project_relationship_experience_advisory
from aura_relationship_experience import (
    RelationshipExperienceObservation,
    RelationshipHumanDisposition,
    RelationshipOutcome,
    crucible_replay_scenarios,
    project_relationship_timeline,
)


def _schema(name: str) -> dict:
    return json.loads((Path(__file__).resolve().parents[1] / "schemas" / name).read_text(encoding="utf-8"))


def _participant(pid: str, symbol: str, role: str, *, grounded: bool = True) -> dict:
    metadata = {
        "file_path": f"{symbol.lower()}.py",
        "tests": [f"tests/test_{symbol.lower()}.py"],
    }
    if grounded:
        metadata.update(
            source_hash=(pid[-1] * 64),
            file_source_hash=(pid[-1] * 40),
            canonical_ref=f"{symbol.lower()}.py#{symbol}",
        )
    return {
        "participant_id": pid,
        "participant_type": "CALLABLE",
        "qualified_symbol": symbol,
        "role": role,
        "canonical_ref": metadata.get("canonical_ref", ""),
        "metadata": metadata,
    }


def _neighborhood(*, grounded_c: bool = True) -> dict:
    body = {
        "index_digest": "i" * 40,
        "request_digest": "r" * 40,
        "seed_participant_ids": ["relp_a"],
        "participants": [
            _participant("relp_a", "Alpha", "planner"),
            _participant("relp_b", "Beta", "verifier"),
            _participant("relp_c", "Gamma", "adapter", grounded=grounded_c),
        ],
        "relations": [
            {
                "relation_id": "rel_ab",
                "source_participant_id": "relp_a",
                "target_participant_id": "relp_b",
                "relation_type": "CALLS",
                "truth_class": "EXACT_SOURCE",
                "evidence_refs": ["alpha.py#Alpha", "beta.py#Beta"],
            }
        ],
        "metrics": {"participant_count": 3, "relation_count": 1, "candidate_pair_count": 3},
        "truncation_reasons": [],
        "proposal_only": True,
        "safe_to_patch": False,
    }
    return {**body, "neighborhood_digest": stable_digest(body)}


def _compatibility(outcome: str = "COMPATIBLE") -> dict:
    body = {
        "outcome": outcome,
        "required_adapters": [],
        "hard_guard_results": [],
        "proposal_only": True,
    }
    return {**body, "assessment_digest": stable_digest(body)}


def test_c6_bounded_discovery_is_deterministic_and_preserves_rejections() -> None:
    atlas = {
        "assessments": [
            {
                "source_participant_id": "relp_a",
                "target_participant_id": "relp_c",
                "wiring_disposition": "PROHIBITED",
            }
        ]
    }
    one = discover_bounded_emergent_candidates(
        objective="Combine local planner and adapter roles",
        neighborhood=_neighborhood(),
        compatibility=_compatibility(),
        atlas=atlas,
        required_tests=["tests/test_compass.py"],
    )
    two = discover_bounded_emergent_candidates(
        objective="Combine local planner and adapter roles",
        neighborhood=_neighborhood(),
        compatibility=_compatibility(),
        atlas=atlas,
        required_tests=["tests/test_compass.py"],
    )
    assert one.to_dict() == two.to_dict()
    assert one.no_generic_repository_scan is True
    assert any(item.status == "TOO_RISKY" for item in one.candidates)
    assert any(item.status == "FUTURE_PATCHABLE" for item in one.candidates)
    assert any(item["reason"] == "EXACT_RELATION_ALREADY_PRESENT" for item in one.rejected_receipts)
    assert all(
        item.source_evidence_refs and item.target_evidence_refs
        for item in one.candidates
        if item.status == "FUTURE_PATCHABLE"
    )

    verified = verify_bounded_emergent_discovery(one)
    tampered_discovery = one.to_dict()
    tampered_discovery["candidates"][0]["mechanism"] = "tampered"
    with pytest.raises(ValueError, match="discovery digest mismatch"):
        verify_bounded_emergent_discovery(tampered_discovery)
    forbidden_discovery = one.to_dict()
    forbidden_discovery["safe_to_patch"] = True
    forbidden_discovery["discovery_digest"] = stable_digest(
        {key: value for key, value in forbidden_discovery.items() if key != "discovery_digest"}
    )
    with pytest.raises(ValueError, match="authority boundary changed"):
        verify_bounded_emergent_discovery(forbidden_discovery)
    assert verified["summary"]["no_generic_repository_scan"] is True
    assert verified["accepted_candidates"]
    assert any(item["status"] == "TOO_RISKY" for item in verified["rejected_candidates"])
    assert all(item["proposal_only"] for item in verified["accepted_candidates"])


def test_c6_missing_source_evidence_remains_needs_grounding() -> None:
    discovery = discover_bounded_emergent_candidates(
        objective="Try a bounded adapter experiment",
        neighborhood=_neighborhood(grounded_c=False),
        compatibility=_compatibility(),
        required_tests=[],
    )
    assert any(item.status == "NEEDS_GROUNDING" for item in discovery.candidates)
    verified = verify_bounded_emergent_discovery(discovery)
    assert any(item["status"] == "NEEDS_GROUNDING" for item in verified["rejected_candidates"])


def test_c6_pair_budget_truncation_is_receipted() -> None:
    neighborhood = _neighborhood()
    neighborhood["participants"].append(_participant("relp_d", "Delta", "observer"))
    body = dict(neighborhood)
    body.pop("neighborhood_digest", None)
    neighborhood["neighborhood_digest"] = stable_digest(body)
    discovery = discover_bounded_emergent_candidates(
        objective="Bound pair exploration",
        neighborhood=neighborhood,
        compatibility=_compatibility(),
        max_pairs_considered=1,
    )
    assert any(item["reason"] == "PAIR_BUDGET_TRUNCATED" for item in discovery.suppressed_receipts)


def _compass_packet() -> dict:
    return {
        "objective": "Compile final relationship work",
        "grounding_digest": "g" * 48,
        "grounding_ok": True,
        "recommended_targets": [
            {
                "file_path": "alpha.py",
                "symbol": "Alpha.run",
                "line_start": 10,
                "line_end": 24,
                "source_hash": "a" * 64,
                "file_source_hash": "b" * 64,
            },
            {
                "file_path": "beta.py",
                "symbol": "Beta.verify",
                "line_start": 4,
                "line_end": 12,
                "source_hash": "c" * 64,
                "file_source_hash": "d" * 64,
            },
        ],
        "required_tests": ["tests/test_alpha.py", "tests/test_beta.py"],
        "required_adapters": ["schema_adapter"],
        "prohibitions": [{"pattern": "self_verification_block"}],
        "emergent_evidence": {"risk_map": [{"risk": "cross-module regression"}]},
        "bounded_emergent_verification": {
            "accepted_candidates": [
                {
                    "candidate_id": "bem_one",
                    "smallest_experiment": "Run a read-only fixture.",
                    "failure_conditions": ["test fails"],
                    "evidence_refs": ["alpha.py#Alpha.run"],
                }
            ]
        },
    }


def test_c7_change_graph_capsules_and_agent_ir_are_proposal_only() -> None:
    graph = build_compass_change_graph(_compass_packet())
    assert validate_compass_change_graph(graph)["ok"] is True
    types = {item["node_type"] for item in graph["nodes"]}
    assert {
        "ACTION",
        "TEST",
        "RISK",
        "ADAPTER",
        "PROHIBITION",
        "EXPERIMENT",
        "PROOF",
        "ROLLBACK",
        "HUMAN_DECISION",
    }.issubset(types)
    assert graph["phase_capsules"]

    capsules = compile_compass_act_capsules(graph)
    assert capsules["ok"] is True
    assert capsules["act_capsules"]
    assert all(item["proposal_only"] for item in capsules["act_capsules"])
    assert all(item["automatic_merge"] is False for item in capsules["act_capsules"])
    assert all(item["surgeon_request"]["expected_source_hash"] for item in capsules["act_capsules"])
    validator = jsonschema.Draft202012Validator(_schema("aura_compass_act_capsule.schema.json"))
    for capsule in capsules["act_capsules"]:
        validator.validate(capsule)

    agent_ir = AgentIRCompiler.compile_compass_act_capsules(capsules)
    tampered_capsules = deepcopy(capsules)
    tampered_capsules["act_capsules"][0]["target_file"] = "tampered.py"
    with pytest.raises(ValueError, match="capsule digest mismatch"):
        AgentIRCompiler.compile_compass_act_capsules(tampered_capsules)
    assert agent_ir["ok"] is True
    assert agent_ir["floor"] == "SPEC"
    assert all(item["payload"]["proposal_only"] for item in agent_ir["nodes"])


def test_c7_capsule_compiler_fails_closed_on_missing_hash_or_tests() -> None:
    packet = _compass_packet()
    packet["recommended_targets"][0]["source_hash"] = ""
    graph = build_compass_change_graph(packet)
    result = compile_compass_act_capsules(graph)
    assert result["ok"] is False
    assert result["fail_closed"] is True
    assert result["reason"] == "CAPSULE_EVIDENCE_INCOMPLETE"

    tampered = deepcopy(build_compass_change_graph(_compass_packet()))
    tampered["nodes"][0]["payload"]["target_file"] = "tampered.py"
    with pytest.raises(ValueError, match="digest mismatch"):
        validate_compass_change_graph(tampered)

    forbidden = deepcopy(build_compass_change_graph(_compass_packet()))
    forbidden["authority"]["merge_authority"] = True
    forbidden["graph_digest"] = stable_digest({key: value for key, value in forbidden.items() if key != "graph_digest"})
    with pytest.raises(ValueError, match="authority boundary changed"):
        validate_compass_change_graph(forbidden)

    no_actions = _compass_packet()
    no_actions["recommended_targets"] = []
    empty_result = compile_compass_act_capsules(build_compass_change_graph(no_actions))
    assert empty_result["reason"] == "NO_ACTION_NODES"


def test_c7_failure_routing_separates_surgeon_from_council() -> None:
    assert route_compass_failure_classes(["LOCAL_ASSERTION"])["route"] == "SURGEON"
    structural = route_compass_failure_classes(["INTERFACE", "INVARIANT"])
    assert structural["route"] == "COUNCIL_V3"
    assert "continuity" in structural["critic_lanes"]
    assert "rollback" in structural["critic_lanes"]


def _observation(*, head: str = "h1", outcome: RelationshipOutcome = RelationshipOutcome.SUCCESS, tx: float = 1000.0):
    return RelationshipExperienceObservation.create(
        relationship_id="bem_one",
        relationship_digest="d" * 40,
        repository_head=head,
        working_tree_digest="w" * 40,
        valid_from_head=head,
        outcome=outcome,
        verifier_evidence_refs=["pytest:tests/test_alpha.py"],
        receipt_refs=["compass:receipt-1"],
        source_refs=["alpha.py#Alpha.run"],
        current_source_digest="s" * 40,
        human_disposition=RelationshipHumanDisposition.APPROVED,
        privacy_class="PROJECT",
        transaction_time=tx,
        objective_digest="o" * 40,
    )


def test_c8_bitemporal_experience_is_append_only_rebuildable_and_advisory(tmp_path: Path) -> None:
    current = _observation()
    stale = _observation(head="old", outcome=RelationshipOutcome.FAILURE, tx=500.0)

    jsonschema.Draft202012Validator(_schema("aura_relationship_experience.schema.json")).validate(current.to_dict())
    gate = current.lesson_eligibility(
        current_repository_head="h1",
        current_source_digest="s" * 40,
        privacy_check_passed=True,
    )
    assert gate["eligible"] is True

    timeline = project_relationship_timeline([current, stale], current_repository_head="h1", now=2000.0)
    assert timeline["historical_facts_overwritten"] is False
    assert timeline["decay_affects_validity"] is False
    assert timeline["timeline"][0]["stale"] is True
    assert timeline["timeline"][1]["stale"] is False

    with ArenaExperienceLedger(tmp_path) as ledger:
        first = ledger.record_relationship_observation(current)
        replay = ledger.record_relationship_observation(current)
        assert first["ok"] is True
        assert replay["idempotent_replay"] is True
        assert ledger.status()["relationship_experience_count"] == 1
        history = ledger.relationship_history(relationship_id="bem_one")
        assert len(history) == 1
        rebuilt = ledger.rebuild_relationship_projection([current.to_dict()])
        assert rebuilt["recoverable_from_canonical_receipts"] is True
        assert rebuilt["idempotent"] == 1

    qdkt = project_relationship_experience_advisory(current)
    assert qdkt["truth_class"] == "DERIVED_EXPERIENCE_ADVISORY"
    assert qdkt["canonical_relation_validity"] is False
    replay = crucible_replay_scenarios(
        [current],
        current_repository_head="h1",
        current_source_digests={"bem_one": "s" * 40},
        privacy_check_passed=True,
    )
    assert replay["scenarios"]
    assert replay["scenarios"][0]["proposal_only"] is True


def test_c9_rollout_gate_requires_complete_paired_live_authorization() -> None:
    shadow = validate_compass_rollout(CompassRolloutMode.SHADOW)
    assert shadow["admitted"] is True
    limited = validate_compass_rollout("LIMITED")
    assert limited["admitted"] is False
    assert limited["missing"] == ["verifier_ref"]
    assert validate_compass_rollout("LIMITED", verifier_ref="quality:receipt")["admitted"] is True
    paired = validate_compass_rollout("PAIRED_LIVE")
    assert paired["admitted"] is False
    assert set(paired["missing"]) == {"provider", "budget", "nonce", "verifier_ref"}
    with pytest.raises(ValueError, match="unsupported Compass rollout budget fields"):
        validate_compass_rollout("SHADOW", budget={"arbitrary": 1})
    with pytest.raises(ValueError, match="must be positive"):
        validate_compass_rollout("SHADOW", budget={"max_tokens": True})
    authorized = validate_compass_rollout(
        "PAIRED_LIVE",
        provider="fixture-provider",
        budget={"max_tokens": 1000},
        nonce="nonce",
        verifier_ref="verifier:fixture",
    )
    assert authorized["admitted"] is True
    assert authorized["provider_execution_authorized"] is False


def _fake_final_packet() -> dict:
    graph = build_compass_change_graph(_compass_packet())
    capsules = compile_compass_act_capsules(graph)
    return {
        "compass_digest": "run-final",
        "grounding_digest": "grounding-final",
        "route": "CODING_RELATIONSHIP_COMPASS",
        "target_file": "alpha.py",
        "target_symbol": "Alpha.run",
        "recommended_targets": _compass_packet()["recommended_targets"],
        "relational_neighborhood": {
            "neighborhood_digest": "neighborhood-final",
            "participants": _neighborhood()["participants"],
            "relations": _neighborhood()["relations"],
            "metrics": {"participant_count": 3},
            "truncation_reasons": [],
        },
        "atlas": {"snapshot_digest": "atlas-final", "profile": "OBJECTIVE_STANDARD", "assessments": []},
        "prohibitions": [],
        "missing_roles": [],
        "required_adapters": [],
        "bounded_emergent_discovery": {"candidates": []},
        "bounded_emergent_verification": {"accepted_candidates": [], "rejected_candidates": []},
        "typed_compatibility": {"outcome": "COMPATIBLE"},
        "coding_breadboard": {"receipt_digest": "breadboard-final"},
        "change_graph": graph,
        "phase_capsules": graph["phase_capsules"],
        "act_capsules": capsules,
        "agent_ir": AgentIRCompiler.compile_compass_act_capsules(capsules),
        "council_route": route_compass_failure_classes([]),
        "rollout": validate_compass_rollout("SHADOW"),
    }


def test_c9_bridge_and_mcp_expose_six_bounded_tools(monkeypatch, tmp_path: Path) -> None:
    import aura_coding_relationship_compass as compass_module

    monkeypatch.setattr(compass_module, "compile_coding_relationship_compass", lambda *args, **kwargs: _fake_final_packet())
    bridge = PersistentAuraAgentArenaBridge(repo_root=str(tmp_path))
    try:
        prepared = bridge.aura_compass_prepare(objective="Use the Coding Relationship Compass")
        assert prepared["run_id"] == "run-final"
        neighborhood_projection = bridge.aura_compass_neighborhood("run-final")
        assert neighborhood_projection["neighborhood_digest"] == "neighborhood-final"
        assert neighborhood_projection["interface_truncation"]["participants_omitted"] == 0
        classification_projection = bridge.aura_compass_classify("run-final")
        assert classification_projection["atlas_digest"] == "atlas-final"
        assert classification_projection["interface_truncation"]["assessments_omitted"] == 0
        assert bridge.aura_compass_breadboard("run-final")["coding_breadboard"]["receipt_digest"] == "breadboard-final"
        plan_projection = bridge.aura_compass_plan("run-final")
        assert plan_projection["phase_capsules"]
        assert plan_projection["interface_truncation"]["nodes_omitted"] == 0
        compiled = bridge.aura_compass_compile_capsules("run-final")
        assert compiled["provider_execution_authorized"] is False
        assert compiled["automatic_merge"] is False

        response = handle_request(
            bridge,
            {
                "jsonrpc": "2.0",
                "id": 91,
                "method": "tools/call",
                "params": {"name": "aura_compass_plan", "arguments": {"run_id": "run-final"}},
            },
        )
        result = json.loads(response["result"]["content"][0]["text"])
        assert result["ok"] is True
        assert result["proposal_only"] is True
    finally:
        bridge.persistence.registry  # keep object reachable until close paths complete

    names = {item["name"] for item in TOOL_DEFINITIONS}
    from aura_affordance_directory import SEED_AFFORDANCES
    affordance_ids = [item["id"] for item in SEED_AFFORDANCES]
    assert len(affordance_ids) == len(set(affordance_ids))
    assert {
        "aura_compass_prepare",
        "aura_compass_neighborhood",
        "aura_compass_classify",
        "aura_compass_breadboard",
        "aura_compass_plan",
        "aura_compass_compile_capsules",
    }.issubset(names)
