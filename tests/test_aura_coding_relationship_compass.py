from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path

import aura_coding_relationship_compass as compass
from aura_live_architect import ArchitectFusionCouncil, ArchitectModelRouter
from aura_relationship_atlas import (
    build_relationship_atlas,
    load_relationship_atlas,
    validate_relationship_atlas,
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
    return {
        "index_digest": "index-digest",
        "repository_identity": {
            "repo_head": "a" * 40,
            "working_tree_digest": "worktree-digest",
            "codemap_digest": "codemap-digest",
            "topology_digest": "topology-digest",
            "connectome_graph_digest": "connectome-digest",
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
    index["participants"][0]["qualified_symbol"] = "compile_coding_relationship_compass"
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
    assert packet["prohibitions"]
    assert packet["safe_to_patch"] is False


def test_injected_evidence_rejects_forged_file_hash(monkeypatch, tmp_path: Path) -> None:
    source_text = "def target():\n    return 1\n"
    (tmp_path / "target.py").write_text(source_text, encoding="utf-8")
    monkeypatch.setattr(compass, "_repository_head", lambda root: "b" * 40)
    packet = {
        "repo_head": "b" * 40,
        "atomic_inventory": {
            "selected_atomic_functions": [{
                "file_path": "target.py", "line_start": 1, "line_end": 2,
                "source_hash": hashlib.sha256(source_text.rstrip("\n").encode()).hexdigest(),
                "file_source_hash": "0" * 64,
            }]
        },
        "source_slices": [],
    }
    try:
        compass._validate_injected_evidence_packet(tmp_path, packet)
    except ValueError as exc:
        assert "file hash mismatch" in str(exc)
    else:
        raise AssertionError("forged injected evidence must fail closed")


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
