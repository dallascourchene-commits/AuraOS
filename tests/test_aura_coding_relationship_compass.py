from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path

import pytest

import aura_change_graph as change_graph
import aura_coding_relationship_compass as compass
from aura_event_contracts import stable_digest
import aura_live_architect as live_architect
import aura_relationship_atlas as atlas_module
from aura_live_architect import ArchitectFusionCouncil, ArchitectModelRouter
from aura_relationship_contracts import RelationalNeighborhoodRequest, SourceReference
from aura_relationship_atlas import (
    build_relationship_atlas,
    load_relationship_atlas,
    validate_relationship_atlas,
)


@pytest.fixture(autouse=True)
def _bind_index_identity_to_fixture(monkeypatch) -> None:
    monkeypatch.setattr(
        atlas_module,
        "_current_relational_index_identity",
        lambda repo_root, relational_index: dict(
            relational_index.get("repository_identity") or {}
        ),
    )


def _minimal_relational_index() -> dict:
    participants = [
        {
            "participant_id": "relp_source",
            "digest": "a" * 64,
            "participant_type": "atomic_symbol",
            "canonical_owner": "CodeTopoAnchor",
            "canonical_ref": "aura_example.py#function:source",
            "freshness": "CURRENT",
            "role": "source",
            "truth_class": "EXACT_SOURCE",
            "evidence_refs": ["source:aura_example.py:1-2"],
            "qualified_symbol": "source",
            "metadata": {"file_path": "aura_example.py", "line_start": 1},
        },
        {
            "participant_id": "relp_target",
            "digest": "b" * 64,
            "participant_type": "atomic_symbol",
            "canonical_owner": "CodeTopoAnchor",
            "canonical_ref": "aura_example.py#function:target",
            "freshness": "CURRENT",
            "role": "target",
            "truth_class": "EXACT_SOURCE",
            "evidence_refs": ["source:aura_example.py:4-5"],
            "qualified_symbol": "target",
            "metadata": {"file_path": "aura_example.py", "line_start": 4},
        },
    ]
    body = {
        "repository_identity": {
            "repo_head": "a" * 40,
            "working_tree_digest": "worktree-digest",
            "codemap_digest": "codemap-digest",
            "topology_digest": "topology-digest",
            "connectome_graph_digest": "graph-digest",
            "atomic_inventory_digest": "atomic-digest",
            "profile_digest": "profile-digest",
        },
        "participants": participants,
        "relations": [
            {
                "relation_id": "relation_source_target",
                "source_participant_id": "relp_source",
                "target_participant_id": "relp_target",
                "relation_type": "CALLS",
                "truth_class": "EXACT_SOURCE",
                "required": True,
                "evidence_refs": ["source:aura_example.py:2"],
            }
        ],
        "groups": [],
        "reverse_indexes": {
            "by_file_path": {"aura_example.py": ["relp_source", "relp_target"]},
            "by_qualified_symbol": {
                "aura_example.py#source": ["relp_source"],
                "aura_example.py#target": ["relp_target"],
            },
        },
    }
    return {**body, "index_digest": stable_digest(body, digest_size=20)}


def _rebind_index_digest(index: dict) -> None:
    body = dict(index)
    body.pop("index_digest", None)
    index["index_digest"] = stable_digest(body, digest_size=20)


def test_atlas_supports_validated_nonpersistent_compile_and_loader(tmp_path: Path) -> None:
    snapshot = build_relationship_atlas(
        repo_root=tmp_path,
        relational_index_data=_minimal_relational_index(),
        profile="MINIMAL",
        persist=False,
    )
    assert validate_relationship_atlas(snapshot)["ok"] is True
    assert len(snapshot.assessments) == 1
    assert not (tmp_path / ".aura").exists()

    path = tmp_path / "atlas.json"
    path.write_text(json.dumps(snapshot.to_dict()), encoding="utf-8")
    loaded = load_relationship_atlas(path)
    assert loaded.snapshot_digest == snapshot.snapshot_digest
    assert loaded.assessments[0].relation_types == ["CALLS"]


def test_compass_intent_and_grounding_projection() -> None:
    assert compass.is_coding_relationship_compass_intent(
        "Make a function combining Connectome, Relational Synthesis, and Atlas to code better"
    )
    assert not compass.is_coding_relationship_compass_intent("Explain the weather")
    assert not compass.is_coding_relationship_compass_intent(
        "Scan the repository and consolidate memory, skill, capability, and agentic "
        "functions to improve the Human Agent Arena."
    )
    assert compass.is_coding_relationship_compass_intent(
        "Use the Atlas to ground this coding refactor"
    )

    grounding = compass.relationship_compass_grounding(
        {
            "route": "CODING_RELATIONSHIP_COMPASS",
            "target_file": "aura_coding_relationship_compass.py",
            "target_symbol": "compile_coding_relationship_compass",
            "compass_digest": "digest",
            "recommended_targets": [
                {
                    "file_path": "aura_coding_relationship_compass.py",
                    "symbol": "compile_coding_relationship_compass",
                    "line_start": 1,
                    "line_end": 10,
                    "source_hash": "source-hash",
                    "file_source_hash": "file-hash",
                }
            ],
            "required_tests": ["tests/test_aura_coding_relationship_compass.py"],
            "connectome": {"required_capability_ids": ["aura.relational.index"]},
            "atlas": {"snapshot_digest": "atlas-digest"},
            "relationships_to_preserve": [{"relation_types": ["CALLS"]}],
            "prohibitions": [{"pattern": "self_verification_block"}],
            "missing_roles": ["verifier"],
            "required_adapters": ["bounded_projection"],
            "action_capsule_hints": [{"task_id": "CRC-01"}],
            "grounding_ok": True,
        }
    )
    assert grounding["target_file"] == "aura_coding_relationship_compass.py"
    assert grounding["target_symbol"] == "compile_coding_relationship_compass"
    assert grounding["safe_to_patch"] is False
    assert grounding["human_review_required"] is True


def test_compass_preserves_qualified_method_symbols_across_source_bindings() -> None:
    method = {
        "file_path": "service.py",
        "symbol": "run",
        "qualified_symbol": "Alpha.run",
        "line_start": 4,
        "line_end": 6,
        "source_hash": "source-hash",
        "file_source_hash": "file-hash",
    }
    evidence = {
        "atomic_inventory": {"selected_atomic_functions": [method]},
        "source_slices": [method],
    }

    refs = compass._source_references_from_evidence(evidence)

    assert len(refs) == 1
    assert refs[0].symbol == "Alpha.run"
    assert compass._canonical_grounding_binding(method)["symbol"] == "Alpha.run"
    assert change_graph._canonical_target_binding(method)["symbol"] == "Alpha.run"


def test_legacy_neighborhood_disambiguates_source_refs_by_span_and_hash() -> None:
    legacy = _minimal_relational_index()
    legacy["participants"] = [
        {
            "participant_id": "first_run",
            "digest": "1" * 64,
            "qualified_symbol": "Alpha.run",
            "metadata": {
                "file_path": "service.py",
                "line_start": 2,
                "line_end": 3,
                "file_source_hash": "f" * 64,
            },
        },
        {
            "participant_id": "second_run",
            "digest": "2" * 64,
            "qualified_symbol": "Alpha.run",
            "metadata": {
                "file_path": "service.py",
                "line_start": 5,
                "line_end": 6,
                "file_source_hash": "f" * 64,
            },
        },
    ]
    legacy["relations"] = []
    _rebind_index_digest(legacy)
    source_ref = SourceReference(
        file_path="service.py",
        symbol="Alpha.run",
        line_start=2,
        line_end=3,
        source_hash="1" * 64,
        file_source_hash="f" * 64,
    )
    request = RelationalNeighborhoodRequest(
        objective_digest="legacy-redefined-method",
        seed_participant_ids=(),
        seed_source_refs=(source_ref,),
        max_hops=1,
        max_nodes=8,
        max_edges=16,
    )

    packet = compass._compatibility_neighborhood_from_raw_index(request, legacy)

    assert packet["seed_participant_ids"] == ["first_run"]
    assert [item["participant_id"] for item in packet["participants"]] == ["first_run"]
    with pytest.raises(
        ValueError,
        match="legacy relational neighborhood source ref must resolve to exactly one",
    ):
        compass._compatibility_neighborhood_from_raw_index(
            RelationalNeighborhoodRequest(
                objective_digest="legacy-redefined-method-drift",
                seed_participant_ids=(),
                seed_source_refs=(
                    SourceReference(
                        **{**source_ref.to_dict(), "source_hash": "0" * 64}
                    ),
                ),
                max_hops=1,
                max_nodes=8,
                max_edges=16,
            ),
            legacy,
        )


def test_legacy_neighborhood_resolves_unqualified_method_source_ref() -> None:
    legacy = _minimal_relational_index()
    legacy["participants"] = [
        {
            "participant_id": "alpha_run",
            "digest": "1" * 64,
            "qualified_symbol": "Alpha.run",
            "metadata": {
                "file_path": "service.py",
                "line_start": 2,
                "line_end": 3,
                "file_source_hash": "f" * 64,
            },
        }
    ]
    legacy["relations"] = []
    _rebind_index_digest(legacy)
    request = RelationalNeighborhoodRequest(
        objective_digest="legacy-unqualified-method",
        seed_participant_ids=(),
        seed_source_refs=(
            SourceReference(
                file_path="service.py",
                symbol="run",
                line_start=2,
                line_end=3,
                source_hash="1" * 64,
                file_source_hash="f" * 64,
            ),
        ),
        max_hops=1,
        max_nodes=8,
        max_edges=16,
    )

    packet = compass._compatibility_neighborhood_from_raw_index(request, legacy)

    assert packet["seed_participant_ids"] == ["alpha_run"]


def test_compile_compass_combines_all_four_planes(monkeypatch, tmp_path: Path) -> None:
    source_text = "def compile_coding_relationship_compass():\n    return None\n"
    (tmp_path / "aura_coding_relationship_compass.py").write_text(source_text, encoding="utf-8")
    file_hash = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    source_hash = hashlib.sha256(source_text.rstrip("\n").encode("utf-8")).hexdigest()
    monkeypatch.setattr(compass, "_repository_head", lambda root: "a" * 40)
    monkeypatch.setattr(
        compass,
        "build_capability_connectome",
        lambda root: {"ok": True, "version": "V1", "nodes": [], "edges": []},
    )
    monkeypatch.setattr(
        compass,
        "enrich_connectome",
        lambda graph: {**graph, "version": "V2", "graph_digest": "graph-digest"},
    )
    monkeypatch.setattr(
        compass,
        "find_capability_path",
        lambda objective, root: {"ok": True, "path": ["aura.relational.index"]},
    )
    monkeypatch.setattr(
        compass,
        "enrich_path",
        lambda packet, graph: {
            **packet,
            "path_digest": "path-digest",
            "required_capability_ids": ["aura.relational.index"],
            "path_details": [],
            "implemented_by": [],
            "symbols": [],
            "tests": [],
            "deterministic_capability_ids": ["aura.relational.index"],
            "model_dependent_capability_ids": [],
            "unresolved_execution_capability_ids": [],
        },
    )

    evidence = {
        "ok": True,
        "grounding_ok": True,
        "packet_id": "packet-id",
        "packet_digest": "packet-digest",
        "repo_head": "a" * 40,
        "status": "GROUNDED_ATOMIC_CLOSURE",
        "atomic_inventory": {
            "inventory_digest": "atomic-digest",
            "total_count": 1,
            "selected_atomic_functions": [
                {
                    "file_path": "aura_coding_relationship_compass.py",
                    "symbol": "compile_coding_relationship_compass",
                    "qualified_symbol": "compile_coding_relationship_compass",
                    "line_start": 1,
                    "line_end": 2,
                    "source_hash": source_hash,
                    "file_source_hash": file_hash,
                }
            ],
        },
        "source_slices": [
            {
                "file_path": "aura_coding_relationship_compass.py",
                "symbol": "compile_coding_relationship_compass",
                "qualified_symbol": "compile_coding_relationship_compass",
                "line_start": 1,
                "line_end": 2,
                "source_hash": source_hash,
                "file_source_hash": file_hash,
                "node_id": "node-id",
            }
        ],
        "dependency_edges": [],
        "selected_findings": [],
        "risk_map": [],
        "tests": ["tests/test_compass.py"],
        "required_tests": ["tests/test_compass.py"],
    }
    monkeypatch.setattr(
        compass,
        "compile_relational_shadow_capsule",
        lambda *args, **kwargs: {
            "schema_version": "AURA_RELATIONAL_SYNTHESIS_CAPSULE_V1",
            "capsule_digest": "capsule-digest",
            "shadow_mode": True,
            "safe_to_patch": False,
        },
    )
    index = _minimal_relational_index()
    index["participants"][0]["metadata"]["file_path"] = "aura_coding_relationship_compass.py"
    index["participants"][0]["metadata"]["line_start"] = 1
    index["participants"][0]["metadata"]["line_end"] = 2
    index["participants"][0]["metadata"]["file_source_hash"] = file_hash
    index["participants"][0]["qualified_symbol"] = "compile_coding_relationship_compass"
    index["participants"][0]["digest"] = source_hash
    _rebind_index_digest(index)
    atlas = build_relationship_atlas(
        repo_root=tmp_path,
        relational_index_data=index,
        profile="MINIMAL",
        persist=False,
    )

    packet = compass.compile_coding_relationship_compass(
        "combine Connectome Relational Synthesis and Atlas to code better",
        tmp_path,
        evidence_packet=evidence,
        relational_index_data=index,
        atlas_snapshot=atlas,
    )
    assert packet["target_file"] == "aura_coding_relationship_compass.py"
    assert packet["target_symbol"] == "compile_coding_relationship_compass"
    assert packet["connectome"]["graph_digest"] == "graph-digest"
    assert packet["relational_synthesis"]["capsule_digest"] == "capsule-digest"
    assert packet["atlas"]["snapshot_digest"] == atlas.snapshot_digest
    assert packet["relational_neighborhood"]["neighborhood_digest"]
    assert packet["relational_neighborhood"]["compatibility_projection"] is True
    assert packet["typed_compatibility"]["outcome"] in {"COMPATIBLE", "ADAPTER_REQUIRED"}
    assert packet["coding_breadboard"]["receipt_digest"]
    assert packet["coding_breadboard"]["authority"]["execution_authority"] is False
    assert packet["bounded_emergent_discovery"]["discovery_digest"]
    assert packet["bounded_emergent_verification"]["verification_digest"]
    assert packet["change_graph"]["graph_digest"]
    assert packet["phase_capsules"]
    assert packet["act_capsules"]["ok"] is True
    assert packet["agent_ir"]["ok"] is True
    assert packet["rollout"]["mode"] == "SHADOW"
    assert packet["experience_projection_template"]["eligibility_gate_closed_by_default"] is True
    assert packet["prohibitions"]
    assert packet["safe_to_patch"] is False


def test_invalid_paired_live_rollout_fails_before_grounding(monkeypatch, tmp_path: Path) -> None:
    def unexpected_grounding(*args, **kwargs):
        raise AssertionError("grounding must not run before rollout admission")

    monkeypatch.setattr(compass, "build_capability_connectome", unexpected_grounding)

    with pytest.raises(
        ValueError,
        match="PAIRED_LIVE Compass rollout requires provider, budget, nonce, and verifier_ref",
    ):
        compass.compile_coding_relationship_compass(
            "combine Connectome and Atlas",
            tmp_path,
            rollout_mode="PAIRED_LIVE",
        )


def test_supplied_atlas_rejects_stale_source_identity(tmp_path: Path) -> None:
    index = _minimal_relational_index()
    atlas = build_relationship_atlas(
        repo_root=tmp_path,
        relational_index_data=index,
        profile="MINIMAL",
        persist=False,
    )
    current_index = json.loads(json.dumps(index))
    current_index["repository_identity"]["repo_head"] = "b" * 40
    _rebind_index_digest(current_index)

    with pytest.raises(ValueError, match="stale or belongs to different evidence"):
        compass._validate_supplied_atlas_snapshot(
            atlas,
            evidence={
                "repo_head": "b" * 40,
                "atomic_inventory": {"inventory_digest": "atomic-digest"},
            },
            relational_index=current_index,
            connectome={"graph_digest": "graph-digest"},
        )


def test_supplied_atlas_rejects_tampered_relational_index_content(tmp_path: Path) -> None:
    index = _minimal_relational_index()
    atlas = build_relationship_atlas(
        repo_root=tmp_path,
        relational_index_data=index,
        profile="MINIMAL",
        persist=False,
    )
    tampered_index = json.loads(json.dumps(index))
    tampered_index["participants"][0]["role"] = "tampered_role"

    with pytest.raises(ValueError, match="relational index digest mismatch"):
        compass._validate_supplied_atlas_snapshot(
            atlas,
            evidence={
                "repo_head": "a" * 40,
                "atomic_inventory": {"inventory_digest": "atomic-digest"},
            },
            relational_index=tampered_index,
            connectome={"graph_digest": "graph-digest"},
        )


def test_supplied_atlas_rejects_post_construction_tampering(tmp_path: Path) -> None:
    index = _minimal_relational_index()
    atlas = build_relationship_atlas(
        repo_root=tmp_path,
        relational_index_data=index,
        profile="MINIMAL",
        persist=False,
    )
    atlas.boundary["tampered"] = True

    with pytest.raises(ValueError, match="failed integrity validation"):
        compass._validate_supplied_atlas_snapshot(
            atlas,
            evidence={
                "repo_head": "a" * 40,
                "atomic_inventory": {"inventory_digest": "atomic-digest"},
            },
            relational_index=index,
            connectome={"graph_digest": "graph-digest"},
        )


def test_architect_refuses_when_admitted_compass_grounding_fails(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(compass, "is_coding_relationship_compass_intent", lambda intent: True)

    def fail_compile(*args, **kwargs):
        raise ValueError("stale exact evidence")

    monkeypatch.setattr(compass, "compile_coding_relationship_compass", fail_compile)

    def forbidden_fallback(*args, **kwargs):
        raise AssertionError("legacy grounding fallback must not run")

    monkeypatch.setattr(live_architect, "ground_coding_arena_intent", forbidden_fallback)
    router = ArchitectModelRouter(
        repo_root=tmp_path,
        model_caller=None,
        ledger_path=tmp_path / "ledger.jsonl",
    )
    decision = asyncio.run(
        ArchitectFusionCouncil(router).select_plan(
            "architect: combine Connectome, Relational Synthesis, and Atlas to code better"
        )
    )

    assert decision.judge_decision["approved"] is False
    assert decision.selected_plan["status"] == "BLOCKED"
    assert decision.selected_plan["act_tasks"] == []
    assert decision.selected_plan["safe_to_patch"] is False
    assert decision.topological_grounding["relationship_compass_status"] == "FAIL_CLOSED"


def test_injected_evidence_rejects_forged_file_hash(monkeypatch, tmp_path: Path) -> None:
    source_text = "def target():\n    return 1\n"
    (tmp_path / "target.py").write_text(source_text, encoding="utf-8")
    monkeypatch.setattr(compass, "_repository_head", lambda root: "b" * 40)
    packet = {
        "repo_head": "b" * 40,
        "atomic_inventory": {"selected_atomic_functions": []},
        "source_slices": [{
            "file_path": "target.py", "line_start": 1, "line_end": 2,
            "source_hash": hashlib.sha256(source_text.rstrip("\n").encode()).hexdigest(),
            "file_source_hash": "0" * 64,
        }],
    }
    try:
        compass._validate_injected_evidence_packet(tmp_path, packet)
    except ValueError as exc:
        assert "file hash mismatch" in str(exc)
    else:
        raise AssertionError("forged injected evidence must fail closed")



def test_injected_evidence_accepts_approximate_inventory_with_exact_source_slice(
    monkeypatch, tmp_path: Path
) -> None:
    source_text = "def target():\n    return 1\n"
    (tmp_path / "target.py").write_text(source_text, encoding="utf-8")
    monkeypatch.setattr(compass, "_repository_head", lambda root: "e" * 40)
    file_hash = hashlib.sha256(source_text.encode()).hexdigest()
    source_hash = hashlib.sha256(source_text.rstrip("\n").encode()).hexdigest()
    packet = {
        "repo_head": "e" * 40,
        "atomic_inventory": {
            "selected_atomic_functions": [{
                "file_path": "target.py",
                "symbol": "target",
                "qualified_symbol": "target",
            }]
        },
        "source_slices": [{
            "file_path": "target.py",
            "line_start": 1,
            "line_end": 2,
            "source_hash": source_hash,
            "file_source_hash": file_hash,
        }],
    }

    validated = compass._validate_injected_evidence_packet(tmp_path, packet)

    assert validated["atomic_inventory"]["selected_atomic_functions"][0]["symbol"] == "target"
    assert validated["source_slices"][0] == {
        "file_path": "target.py",
        "line_start": 1,
        "line_end": 2,
        "source_hash": source_hash,
        "file_source_hash": file_hash,
    }

def test_injected_evidence_rejects_stale_head(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(compass, "_repository_head", lambda root: "c" * 40)
    try:
        compass._validate_injected_evidence_packet(tmp_path, {"repo_head": "d" * 40})
    except ValueError as exc:
        assert "current repository HEAD" in str(exc)
    else:
        raise AssertionError("stale injected evidence must fail closed")


def test_architect_uses_compass_before_filename_fallback(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / "aura_coding_relationship_compass.py"
    target.write_text("def compile_coding_relationship_compass():\n    return None\n", encoding="utf-8")
    (tmp_path / "aura_node.py").write_text("pass\n", encoding="utf-8")

    monkeypatch.setattr(compass, "is_coding_relationship_compass_intent", lambda intent: True)
    monkeypatch.setattr(
        compass,
        "compile_coding_relationship_compass",
        lambda *args, **kwargs: {
            "route": "CODING_RELATIONSHIP_COMPASS",
            "target_file": "aura_coding_relationship_compass.py",
            "target_symbol": "compile_coding_relationship_compass",
            "compass_digest": "compass-digest",
            "recommended_targets": [
                {
                    "file_path": "aura_coding_relationship_compass.py",
                    "symbol": "compile_coding_relationship_compass",
                    "line_start": 1,
                    "line_end": 2,
                    "source_hash": "source-hash",
                    "file_source_hash": "file-hash",
                }
            ],
            "required_tests": ["tests/test_aura_coding_relationship_compass.py"],
            "connectome": {"required_capability_ids": ["aura.relational.index"]},
            "atlas": {"snapshot_digest": "atlas-digest"},
            "relationships_to_preserve": [],
            "prohibitions": [],
            "missing_roles": [],
            "required_adapters": [],
            "action_capsule_hints": [],
            "grounding_ok": True,
        },
    )

    router = ArchitectModelRouter(repo_root=tmp_path, model_caller=None, ledger_path=tmp_path / "ledger.jsonl")
    decision = asyncio.run(
        ArchitectFusionCouncil(router).select_plan(
            "architect: make a function combining Connectome, Relational Synthesis, and Atlas to code better"
        )
    )
    assert decision.selected_plan["target_file"] == "aura_coding_relationship_compass.py"
    assert decision.selected_plan["target_symbol"] == "compile_coding_relationship_compass"
    assert decision.selected_plan["source"] == "deterministic_relationship_compass_plan"
