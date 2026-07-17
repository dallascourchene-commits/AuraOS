from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from aura_construction_refactor_plan import (
    CAPABILITY_REQUIREMENTS,
    REQUIRED_STRUCTURES,
    build_construction_capability_reuse_matrix,
    compile_ready_nodes_to_action_capsules,
    create_construction_refactor_skeleton,
    validate_construction_refactor_plan,
)
from aura_refactor_skeleton import (
    RefactorSkeleton,
    RefactorSkeletonNode,
    SourceSpan,
    sha256_file,
)


def fake_resolver(objective, **kwargs):
    files = kwargs.get("target_files", [])
    symbols = kwargs.get("target_symbols", [])
    return {
        "version": "AURA_CAPABILITY_RESOLUTION_V2",
        "topology_health": {"topology_nodes": 10, "topology_edges": 12},
        "exact_matches": [
            {
                "file": files[0],
                "symbol": symbols[0] if symbols else None,
                "kind": "class",
                "grounding_class": "EXACT",
            }
        ],
        "required_capability_ids": ["CAP-EXISTING"],
        "capability_path": ["CAP-EXISTING"],
        "capability_tests": ["tests/test_existing.py"],
        "capability_truth_boundaries": ["advisory_only"],
        "capability_risks": ["scope"],
        "codemap_digest": "codemap",
        "capability_graph_digest": "graph",
        "capability_path_digest": "path",
    }


def test_reuse_matrix_uses_exact_requested_symbols():
    matrix = build_construction_capability_reuse_matrix(resolver=fake_resolver)
    assert matrix["ok"] is True
    assert len(matrix["rows"]) == len(CAPABILITY_REQUIREMENTS)
    assert all(
        row["status"] == "GROUNDED_REUSE_CANDIDATE"
        for row in matrix["rows"]
    )


def test_unrelated_symbol_in_candidate_file_does_not_ground():
    def unrelated(objective, **kwargs):
        files = kwargs.get("target_files", [])
        return {
            "version": "AURA_CAPABILITY_RESOLUTION_V2",
            "topology_health": {"topology_nodes": 10},
            "exact_matches": [
                {
                    "file": files[0],
                    "symbol": "unrelated_function",
                    "kind": "function",
                    "grounding_class": "EXACT",
                }
            ],
            "capability_path": ["GENERIC"],
        }

    matrix = build_construction_capability_reuse_matrix(resolver=unrelated)
    assert matrix["ok"] is False
    assert matrix["unresolved_capability_ids"]


def test_file_placeholder_and_generic_path_do_not_ground():
    def placeholder(objective, **kwargs):
        files = kwargs.get("target_files", [])
        return {
            "version": "AURA_CAPABILITY_RESOLUTION_V2",
            "topology_health": {"topology_nodes": 10},
            "exact_matches": [
                {
                    "file": files[0],
                    "symbol": None,
                    "kind": "file",
                    "grounding_class": "EXACT",
                }
            ],
            "capability_path": ["GENERIC"],
            "reuse_plan": [{"capability_id": "GENERIC"}],
        }

    matrix = build_construction_capability_reuse_matrix(resolver=placeholder)
    assert matrix["ok"] is False


def test_skeleton_foundation_and_deferred_runtime():
    matrix = build_construction_capability_reuse_matrix(resolver=fake_resolver)
    skeleton = create_construction_refactor_skeleton(
        baseline_commit="a" * 40,
        source_plan_digest="b" * 64,
        addendum_digest="c" * 64,
        reuse_matrix=matrix,
    )
    assert [node.node_id for node in skeleton.nodes] == [
        "E0", "E1", "E2", "E3", "E4-E14"
    ]
    assert skeleton.node("E1").status == "GROUNDED"
    assert skeleton.node("E4-E14").reuse_decision == "DEFER"
    assert validate_construction_refactor_plan(skeleton)["ok"] is True
    for node in skeleton.nodes:
        assert {
            item.structure for item in node.integration_dispositions
        } == set(REQUIRED_STRUCTURES)


def test_unresolved_matrix_keeps_e1_closed():
    def unresolved(objective, **kwargs):
        return {
            "version": "AURA_CAPABILITY_RESOLUTION_V2",
            "topology_health": {"topology_nodes": 0},
        }

    matrix = build_construction_capability_reuse_matrix(resolver=unresolved)
    skeleton = create_construction_refactor_skeleton(
        baseline_commit="a" * 40,
        source_plan_digest="b" * 64,
        addendum_digest="c" * 64,
        reuse_matrix=matrix,
    )
    assert skeleton.node("E1").status == "NEEDS_GROUNDING"


@dataclass
class FakeCapsule:
    payload: dict

    def to_dict(self):
        return self.payload


def fake_capsule_factory(**kwargs):
    return FakeCapsule(kwargs)


def integrations():
    return tuple(
        {
            "structure": structure,
            "disposition": "INTEGRATED",
            "reason": "test",
        }
        for structure in REQUIRED_STRUCTURES
    )


def ready_skeleton(tmp_path: Path, *, stale_hash=False, span_end=2):
    source = tmp_path / "plan.py"
    source.write_text("a = 1\nb = 2\n", encoding="utf-8")
    digest = "0" * 64 if stale_hash else sha256_file(source)
    node = RefactorSkeletonNode.create(
        node_id="E3",
        objective="Compile exact grounded code capsule.",
        canonical_owner="aura_liquid_planning_arena.py",
        reuse_decision="ADD_NARROW_ADAPTER",
        target_files=("plan.py",),
        target_symbols=("compile_ready_nodes_to_action_capsules",),
        exact_source_hashes={"plan.py": digest},
        exact_source_spans=(SourceSpan.create("plan.py", 1, span_end),),
        acceptance_criteria=("one bounded diff",),
        required_tests=("tests/test_plan.py",),
        risk_lanes=("scope",),
        status="READY_FOR_ACT",
        integration_dispositions=integrations(),
    )
    return RefactorSkeleton.create(
        objective="test",
        domain="sco_construction_refactor",
        baseline_commit="a" * 40,
        source_plan_digest="b" * 64,
        addendum_digest="c" * 64,
        nodes=(node,),
        status="PLANNED",
    )


def test_unready_capsule_fails_closed(tmp_path):
    matrix = build_construction_capability_reuse_matrix(resolver=fake_resolver)
    skeleton = create_construction_refactor_skeleton(
        baseline_commit="a" * 40,
        source_plan_digest="b" * 64,
        addendum_digest="c" * 64,
        reuse_matrix=matrix,
    )
    result = compile_ready_nodes_to_action_capsules(
        skeleton, repo_root=tmp_path, node_ids=("E3",)
    )
    assert result["ok"] is False
    assert result["error"] == "nodes_not_ready_for_act"


def test_ready_capsule_includes_verified_exact_spans(tmp_path):
    skeleton = ready_skeleton(tmp_path)
    result = compile_ready_nodes_to_action_capsules(
        skeleton,
        repo_root=tmp_path,
        node_ids=("E3",),
        capsule_factory=fake_capsule_factory,
    )
    assert result["ok"] is True
    capsule = result["capsules"][0]
    assert capsule["scope"]["source_hashes"]["plan.py"] == sha256_file(
        tmp_path / "plan.py"
    )
    assert capsule["scope"]["source_spans"] == [
        {"path": "plan.py", "start_line": 1, "end_line": 2}
    ]
    assert "invent missing source hashes or spans" in capsule["forbidden_actions"]


def test_stale_hash_fails_before_capsule_creation(tmp_path):
    skeleton = ready_skeleton(tmp_path, stale_hash=True)
    result = compile_ready_nodes_to_action_capsules(
        skeleton,
        repo_root=tmp_path,
        node_ids=("E3",),
        capsule_factory=fake_capsule_factory,
    )
    assert result["ok"] is False
    assert "source hash mismatch" in str(result["errors"])


def test_out_of_range_span_fails_before_capsule_creation(tmp_path):
    skeleton = ready_skeleton(tmp_path, span_end=99)
    result = compile_ready_nodes_to_action_capsules(
        skeleton,
        repo_root=tmp_path,
        node_ids=("E3",),
        capsule_factory=fake_capsule_factory,
    )
    assert result["ok"] is False
    assert "exceeds file length" in str(result["errors"])


def test_unknown_node_id_fails_closed(tmp_path):
    skeleton = ready_skeleton(tmp_path)
    result = compile_ready_nodes_to_action_capsules(
        skeleton,
        repo_root=tmp_path,
        node_ids=("MISSING",),
        capsule_factory=fake_capsule_factory,
    )
    assert result["ok"] is False
    assert result["error"] == "unknown_skeleton_node_ids"
