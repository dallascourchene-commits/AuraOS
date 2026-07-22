from __future__ import annotations

from copy import deepcopy
import hashlib
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

    verified = verify_bounded_emergent_discovery(one, neighborhood=_neighborhood())
    tampered_discovery = one.to_dict()
    tampered_discovery["candidates"][0]["mechanism"] = "tampered"
    with pytest.raises(ValueError, match="discovery digest mismatch"):
        verify_bounded_emergent_discovery(tampered_discovery, neighborhood=_neighborhood())
    forbidden_discovery = one.to_dict()
    forbidden_discovery["safe_to_patch"] = True
    forbidden_discovery["discovery_digest"] = stable_digest(
        {key: value for key, value in forbidden_discovery.items() if key != "discovery_digest"}
    )
    with pytest.raises(ValueError, match="authority boundary changed"):
        verify_bounded_emergent_discovery(forbidden_discovery, neighborhood=_neighborhood())
    assert verified["summary"]["no_generic_repository_scan"] is True
    assert verified["accepted_candidates"]
    assert any(item["status"] == "TOO_RISKY" for item in verified["rejected_candidates"])
    assert all(item["proposal_only"] for item in verified["accepted_candidates"])
    verification_body = dict(verified)
    verification_digest = verification_body.pop("verification_digest")
    assert verification_digest == stable_digest(verification_body)


def test_c6_verifier_rejects_candidate_supplied_endpoint_hashes() -> None:
    neighborhood = _neighborhood()
    discovery = discover_bounded_emergent_candidates(
        objective="Verify exact endpoint evidence",
        neighborhood=neighborhood,
        compatibility=_compatibility(),
        required_tests=["tests/test_compass.py"],
    ).to_dict()
    future = next(item for item in discovery["candidates"] if item["status"] == "FUTURE_PATCHABLE")
    future["source_source_hashes"] = ["f" * 64]
    discovery["discovery_digest"] = stable_digest(
        {key: value for key, value in discovery.items() if key != "discovery_digest"}
    )
    verified = verify_bounded_emergent_discovery(discovery, neighborhood=neighborhood)
    rejection = next(item for item in verified["rejected_candidates"] if item["candidate_id"] == future["candidate_id"])
    assert "SOURCE_ENDPOINT_HASH_MISMATCH" in rejection["reasons"]
    assert verified["trusted_neighborhood_verified"] is True


def test_c6_missing_source_evidence_remains_needs_grounding() -> None:
    neighborhood = _neighborhood(grounded_c=False)
    discovery = discover_bounded_emergent_candidates(
        objective="Try a bounded adapter experiment",
        neighborhood=neighborhood,
        compatibility=_compatibility(),
        required_tests=[],
    )
    assert any(item.status == "NEEDS_GROUNDING" for item in discovery.candidates)
    verified = verify_bounded_emergent_discovery(discovery, neighborhood=neighborhood)
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


def _write_grounded_source(tmp_path: Path, name: str, prefix: str, line_count: int) -> tuple[str, list[str]]:
    lines = [f"# {prefix} line {index}" for index in range(1, line_count + 1)]
    text = "\n".join(lines) + "\n"
    (tmp_path / name).write_text(text, encoding="utf-8")
    return text, lines


def _compass_packet(tmp_path: Path) -> dict:
    alpha_text, alpha_lines = _write_grounded_source(tmp_path, "alpha.py", "alpha", 30)
    beta_text, beta_lines = _write_grounded_source(tmp_path, "beta.py", "beta", 20)
    targets = [
        {
            "file_path": "alpha.py",
            "symbol": "Alpha.run",
            "line_start": 10,
            "line_end": 24,
            "source_hash": hashlib.sha256("\n".join(alpha_lines[9:24]).encode("utf-8")).hexdigest(),
            "file_source_hash": hashlib.sha256(alpha_text.encode("utf-8")).hexdigest(),
        },
        {
            "file_path": "beta.py",
            "symbol": "Beta.verify",
            "line_start": 4,
            "line_end": 12,
            "source_hash": hashlib.sha256("\n".join(beta_lines[3:12]).encode("utf-8")).hexdigest(),
            "file_source_hash": hashlib.sha256(beta_text.encode("utf-8")).hexdigest(),
        },
    ]
    required_tests = ["tests/test_alpha.py", "tests/test_beta.py"]
    grounding_receipt = {
        "version": "AURA_COMPASS_GROUNDING_RECEIPT_V1",
        "grounding_digest": "g" * 48,
        "repository_head": "h" * 40,
        "evidence_packet_digest": "evidence-packet",
        "atomic_inventory_digest": "inventory-digest",
        "target_bindings": deepcopy(targets),
        "source_evidence_digest": stable_digest(targets),
        "required_tests": required_tests,
        "patch_authority": "exact_source_spans_and_hashes_only",
        "vsa_patch_authority": False,
    }
    return {
        "objective": "Compile final relationship work",
        "grounding_digest": "g" * 48,
        "grounding_ok": True,
        "grounding_receipt": grounding_receipt,
        "grounding_receipt_digest": stable_digest(grounding_receipt),
        "recommended_targets": targets,
        "required_tests": required_tests,
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


def _rebind_grounding_receipt(packet: dict) -> None:
    receipt = packet["grounding_receipt"]
    receipt["target_bindings"] = deepcopy(packet["recommended_targets"])
    receipt["source_evidence_digest"] = stable_digest(receipt["target_bindings"])
    receipt["required_tests"] = list(packet["required_tests"])
    packet["grounding_receipt_digest"] = stable_digest(receipt)


def test_c7_change_graph_capsules_and_agent_ir_are_proposal_only(tmp_path: Path) -> None:
    graph = build_compass_change_graph(_compass_packet(tmp_path), repo_root=tmp_path)
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


def test_c7_change_graph_rejects_unbound_or_drifted_source_evidence(tmp_path: Path) -> None:
    unbound = _compass_packet(tmp_path)
    unbound["recommended_targets"][0]["line_start"] += 1
    with pytest.raises(ValueError, match="not bound"):
        build_compass_change_graph(unbound, repo_root=tmp_path)

    drifted = _compass_packet(tmp_path)
    (tmp_path / "alpha.py").write_text("# repository drift\n", encoding="utf-8")
    with pytest.raises(ValueError, match="file_source_hash mismatch"):
        build_compass_change_graph(drifted, repo_root=tmp_path)


def test_c7_capsule_compiler_fails_closed_on_missing_hash_or_tests(tmp_path: Path) -> None:
    packet = _compass_packet(tmp_path)
    packet["recommended_targets"][0]["source_hash"] = ""
    _rebind_grounding_receipt(packet)
    with pytest.raises(ValueError, match="source_hash"):
        build_compass_change_graph(packet, repo_root=tmp_path)

    packet = _compass_packet(tmp_path)
    packet["required_tests"] = []
    _rebind_grounding_receipt(packet)
    graph = build_compass_change_graph(packet, repo_root=tmp_path)
    result = compile_compass_act_capsules(graph)
    assert result["ok"] is False
    assert result["fail_closed"] is True
    assert result["reason"] == "MISSING_DECLARED_TESTS"

    tampered = deepcopy(build_compass_change_graph(_compass_packet(tmp_path), repo_root=tmp_path))
    tampered["nodes"][0]["payload"]["target_file"] = "tampered.py"
    with pytest.raises(ValueError, match="digest mismatch"):
        validate_compass_change_graph(tampered)

    forbidden = deepcopy(build_compass_change_graph(_compass_packet(tmp_path), repo_root=tmp_path))
    forbidden["authority"]["merge_authority"] = True
    forbidden["graph_digest"] = stable_digest({key: value for key, value in forbidden.items() if key != "graph_digest"})
    with pytest.raises(ValueError, match="authority boundary changed"):
        validate_compass_change_graph(forbidden)

    no_actions = _compass_packet(tmp_path)
    no_actions["recommended_targets"] = []
    _rebind_grounding_receipt(no_actions)
    empty_result = compile_compass_act_capsules(build_compass_change_graph(no_actions, repo_root=tmp_path))
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


def test_c8_private_relationship_observation_requires_pre_redaction(tmp_path: Path) -> None:
    private = RelationshipExperienceObservation.create(
        relationship_id="bem_private",
        relationship_digest="d" * 40,
        repository_head="h1",
        working_tree_digest="w" * 40,
        valid_from_head="h1",
        outcome=RelationshipOutcome.DENIAL,
        verifier_evidence_refs=["pytest:secret_test"],
        receipt_refs=["compass:secret_receipt"],
        source_refs=["private.py#secret"],
        current_source_digest="s" * 40,
        human_disposition=RelationshipHumanDisposition.DENIED,
        privacy_class="PRIVATE_REDACTED",
        transaction_time=1000.0,
        reason="sensitive reason",
    )
    redacted = RelationshipExperienceObservation.create(
        relationship_id="bem_private",
        relationship_digest="d" * 40,
        repository_head="h1",
        working_tree_digest="w" * 40,
        valid_from_head="h1",
        outcome=RelationshipOutcome.DENIAL,
        verifier_evidence_refs=["redacted:verifier"],
        receipt_refs=["redacted:receipt"],
        source_refs=["redacted:source"],
        current_source_digest="s" * 40,
        human_disposition=RelationshipHumanDisposition.DENIED,
        privacy_class="PRIVATE_REDACTED",
        transaction_time=1001.0,
        reason="[REDACTED]",
    )
    with ArenaExperienceLedger(tmp_path) as ledger:
        denied = ledger.record_relationship_observation(private)
        assert denied["ok"] is False
        assert denied["reason"] == "private_relationship_observation_requires_redaction"
        assert denied["observation_id"] == private.observation_id
        assert "experience_id" not in denied
        accepted = ledger.record_relationship_observation(redacted)
        assert accepted["ok"] is True
        payload = ledger.relationship_history(relationship_id="bem_private")[0]
        serialized = json.dumps(payload, sort_keys=True)
        assert "secret_test" not in serialized
        assert "secret_receipt" not in serialized
        assert "private.py#secret" not in serialized
        assert "sensitive reason" not in serialized


def test_c9_classification_projection_bounds_all_collections_and_bytes(tmp_path: Path) -> None:
    bridge = PersistentAuraAgentArenaBridge(repo_root=str(tmp_path))
    huge = "x" * 5000
    bridge._compass_runs["bounded"] = {
        "atlas": {"snapshot_digest": "atlas", "profile": "OBJECTIVE_STANDARD", "assessments": [{"detail": huge}] * 200},
        "prohibitions": [{"detail": huge}] * 100,
        "missing_roles": [huge] * 100,
        "required_adapters": [huge] * 100,
        "bounded_emergent_verification": {
            "version": "V1",
            "verification_digest": "v" * 40,
            "accepted_candidates": [{"detail": huge}] * 100,
            "rejected_candidates": [{"detail": huge}] * 100,
            "suppressed_candidates": [{"detail": huge}] * 100,
            "summary": {"detail": huge},
        },
    }
    projection = bridge.aura_compass_classify("bounded")
    truncation = projection["interface_truncation"]
    assert truncation["assessments_omitted"] == 136
    assert truncation["prohibitions_omitted"] == 36
    assert truncation["missing_roles_omitted"] == 36
    assert truncation["required_adapters_omitted"] == 36
    assert truncation["accepted_candidates_omitted"] == 36
    assert truncation["rejected_candidates_omitted"] == 36
    assert truncation["suppressed_candidates_omitted"] == 36
    assert truncation["response_bytes"] <= truncation["max_response_bytes"]
    assert truncation["bounded_emergent_summary_oversize_replaced"] == 1


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
    with pytest.raises(ValueError, match="must be a positive integer"):
        validate_compass_rollout("SHADOW", budget={"max_calls": 0.1})
    with pytest.raises(ValueError, match="must be a positive integer"):
        validate_compass_rollout("SHADOW", budget={"max_tokens": 1.5})
    with pytest.raises(ValueError, match="must be positive and finite"):
        validate_compass_rollout("SHADOW", budget={"max_cost_usd": float("inf")})
    authorized = validate_compass_rollout(
        "PAIRED_LIVE",
        provider="fixture-provider",
        budget={"max_tokens": 1000},
        nonce="nonce",
        verifier_ref="verifier:fixture",
    )
    assert authorized["admitted"] is True
    assert authorized["provider_execution_authorized"] is False


def _fake_final_packet(tmp_path: Path) -> dict:
    source_packet = _compass_packet(tmp_path)
    graph = build_compass_change_graph(source_packet, repo_root=tmp_path)
    capsules = compile_compass_act_capsules(graph)
    return {
        "compass_digest": "run-final",
        "grounding_digest": "grounding-final",
        "route": "CODING_RELATIONSHIP_COMPASS",
        "target_file": "alpha.py",
        "target_symbol": "Alpha.run",
        "recommended_targets": source_packet["recommended_targets"],
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

    monkeypatch.setattr(compass_module, "compile_coding_relationship_compass", lambda *args, **kwargs: _fake_final_packet(tmp_path))
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


def test_c9_all_compass_projections_bound_adversarial_payloads(monkeypatch, tmp_path: Path) -> None:
    import aura_coding_relationship_compass as compass_module

    huge = "x" * 200_000
    packet = _fake_final_packet(tmp_path)
    packet["rollout"] = {"detail": huge}
    packet["relational_neighborhood"] = {
        "neighborhood_digest": huge,
        "participants": [{"detail": huge}] * 100,
        "relations": [{"detail": huge}] * 300,
        "metrics": {"detail": huge},
        "truncation_reasons": [huge] * 100,
    }
    packet["typed_compatibility"] = {"detail": huge}
    packet["coding_breadboard"] = {"detail": huge}
    packet["change_graph"] = {
        "graph_digest": huge,
        "nodes": [{"detail": huge}] * 300,
    }
    packet["phase_capsules"] = [{"detail": huge}] * 100
    packet["council_route"] = {"detail": huge}
    packet["act_capsules"] = {"ok": True, "detail": huge}
    packet["agent_ir"] = {"detail": huge}
    monkeypatch.setattr(
        compass_module,
        "compile_coding_relationship_compass",
        lambda *args, **kwargs: packet,
    )

    bridge = PersistentAuraAgentArenaBridge(repo_root=str(tmp_path))
    prepared = bridge.aura_compass_prepare(objective="Exercise bounded projections")
    projections = [
        prepared,
        bridge.aura_compass_neighborhood("run-final"),
        bridge.aura_compass_classify("run-final"),
        bridge.aura_compass_breadboard("run-final"),
        bridge.aura_compass_plan("run-final"),
        bridge.aura_compass_compile_capsules("run-final"),
    ]
    for projection in projections:
        receipt = projection["interface_truncation"]
        assert receipt["response_bytes"] <= receipt["max_response_bytes"]
        assert receipt["response_bytes"] == len(
            json.dumps(projection, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        )

    assert prepared["interface_truncation"]["rollout_oversize_replaced"] == 1
    neighborhood_receipt = projections[1]["interface_truncation"]
    assert neighborhood_receipt["participants_oversize_replaced"] == 64
    assert neighborhood_receipt["relations_oversize_replaced"] == 256
    assert neighborhood_receipt["metrics_oversize_replaced"] == 1
    assert neighborhood_receipt["truncation_reasons_oversize_replaced"] == 64
    breadboard_receipt = projections[3]["interface_truncation"]
    assert breadboard_receipt["typed_compatibility_oversize_replaced"] == 1
    assert breadboard_receipt["coding_breadboard_oversize_replaced"] == 1
    plan_receipt = projections[4]["interface_truncation"]
    assert plan_receipt["nodes_oversize_replaced"] == 256
    assert plan_receipt["phase_capsules_oversize_replaced"] == 64
    assert plan_receipt["council_route_oversize_replaced"] == 1
    compile_receipt = projections[5]["interface_truncation"]
    assert compile_receipt["act_capsules_oversize_replaced"] == 1
    assert compile_receipt["agent_ir_oversize_replaced"] == 1


def test_compass_digests_ignore_process_state_fields() -> None:
    import aura_coding_relationship_compass as compass

    one = {
        "relational_neighborhood": {"neighborhood_digest": "n", "index_source": "in_memory_rebuild"},
        "atlas": {"snapshot_digest": "a", "cache_hit": False},
        "value": 1,
    }
    two = deepcopy(one)
    two["relational_neighborhood"]["index_source"] = "process_cache"
    two["atlas"]["cache_hit"] = True
    assert compass._stable_digest(compass._compass_digest_payload(one)) == compass._stable_digest(
        compass._compass_digest_payload(two)
    )


def test_compass_cache_identity_detects_repository_drift(monkeypatch, tmp_path: Path) -> None:
    import aura_coding_relationship_compass as compass

    identity = {
        "repo_head": "h",
        "working_tree_digest": "w1",
        "codemap_digest": "c",
        "topology_digest": "t",
        "topology_version": "v",
        "topology_health": "ok",
        "connectome_graph_digest": "g",
        "connectome_version": "cv",
        "atomic_inventory_digest": "i",
        "atomic_inventory_version": "iv",
        "relation_ontology_digest": "o",
        "profile_digest": "p",
        "schema_digest": "s",
    }
    cached = {"profile": {"name": "MINIMAL"}, "repository_identity": identity}
    observed: dict = {}

    def live_identity(*args, **kwargs):
        observed.update(kwargs)
        return {**identity, "working_tree_digest": "w2"}

    monkeypatch.setattr(compass, "_live_repository_identity", live_identity)
    assert compass._relational_cache_entry_is_current(
        tmp_path,
        cached,
        repo_head="h",
        connectome_graph_digest="g",
        connectome_version="cv",
        atomic_inventory_digest="i",
    ) is False
    assert observed == {
        "repo_head": "h",
        "connectome_graph_digest": "g",
        "connectome_version": "cv",
        "atomic_inventory_digest": "i",
    }
