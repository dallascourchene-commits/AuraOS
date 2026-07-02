import json
from pathlib import Path

from aura_music_coding_arena import (
    BLOCKED,
    PATCH_ELIGIBLE,
    RESEARCH_ANALOGY_ONLY,
    classify_music_result,
    fuse_music_council_plan,
    load_arena_research_ideas,
)


def _write_codemap(root: Path, *, target_symbol: str = "run_live_architect_transaction") -> None:
    aura_dir = root / ".aura"
    aura_dir.mkdir(exist_ok=True)
    (root / "aura_live_architect.py").write_text(
        f"def {target_symbol}():\n    return 1\n",
        encoding="utf-8",
    )
    (root / "test_aura_live_architect.py").write_text(
        f"from aura_live_architect import {target_symbol}\n\n\ndef test_target():\n    assert {target_symbol}() == 1\n",
        encoding="utf-8",
    )
    (aura_dir / "CODEMAP.json").write_text(
        json.dumps(
            {
                "coverage": {
                    "all_included_paths_sorted": [
                        "aura_live_architect.py",
                        "test_aura_live_architect.py",
                    ],
                },
                "file_cards": [
                    {
                        "path": "aura_live_architect.py",
                        "symbols": [{"name": target_symbol, "kind": "function"}],
                        "topology": {"neighbor_files": ["test_aura_live_architect.py"]},
                    }
                ],
                "symbol_index": {
                    target_symbol: [{"file": "aura_live_architect.py", "name": target_symbol, "kind": "function"}],
                },
            }
        ),
        encoding="utf-8",
    )


def _write_research_manifest(root: Path) -> None:
    aura_dir = root / ".aura"
    aura_dir.mkdir(exist_ok=True)
    (aura_dir / "RESEARCH_MANIFEST.json").write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "created_for": "music arena test",
                "papers": [
                    {
                        "arxiv_id": "2407.01489",
                        "label": "Agentless",
                        "target_modules": ["aura_repo_localizer.py", "aura_architect_loop.py"],
                        "implementation_lesson": "Use deterministic localize-first fallbacks when debate fails.",
                        "acceptance_test": "Return candidate files without model calls when Council produces no patch.",
                        "future_ingest": True,
                        "priority": 2,
                    },
                    {
                        "arxiv_id": "2405.15793",
                        "label": "SWE-agent",
                        "target_modules": ["aura_builder_context.py", "aura_live_architect.py"],
                        "implementation_lesson": "Bound every worker through explicit action interfaces and patch output contracts.",
                        "acceptance_test": "Worker prompts include constrained editing tools and diff-only output rules.",
                        "future_ingest": True,
                        "priority": 1,
                    },
                    {
                        "arxiv_id": "2509.06503",
                        "label": "Empirical Research Assistance",
                        "target_modules": ["aura_empirical_software_lab.py", "aura_live_architect.py"],
                        "implementation_lesson": "Turn candidate improvements into measurable sandbox-scored tasks.",
                        "acceptance_test": "Candidate scores are reproducible from local verifier artifacts.",
                        "future_ingest": True,
                        "priority": 0,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


def _candidate(candidate_id: str, decision: str, objective: str, score: float) -> dict:
    return {
        "candidate_id": candidate_id,
        "source": candidate_id,
        "cost_tier": "premium" if candidate_id != "local_free" else "free",
        "score": score,
        "plan": {
            "architecture_decision": decision,
            "target_file": "aura_live_architect.py",
            "target_symbol": "run_live_architect_transaction",
            "objective": "Improve the Coding Arena.",
            "act_tasks": [
                {
                    "task_id": f"A-{candidate_id}",
                    "objective": objective,
                    "target_file": "aura_live_architect.py",
                    "target_symbol": "run_live_architect_transaction",
                    "acceptance": "Patch applies in the temp workspace.",
                    "expected_output": "UNIFIED_DIFF",
                }
            ],
        },
    }


def test_music_coding_arena_fuses_council_plans_with_research(tmp_path: Path):
    _write_codemap(tmp_path)
    _write_research_manifest(tmp_path)
    candidates = [
        _candidate("local_free", "Use deterministic local fallback.", "Keep the Arena bounded.", 0.58),
        _candidate("planner_1", "Use premium planning for broader scope.", "Preserve premium plan intent.", 0.72),
        _candidate("planner_alt_2", "Use empirical scoring and stronger verifier evidence.", "Add verifier-facing evidence.", 0.76),
    ]

    result = fuse_music_council_plan(
        "upgrade Coding Arena with research-guided plan synthesis",
        candidates,
        repo_root=tmp_path,
        target_file="aura_live_architect.py",
        target_symbol="run_live_architect_transaction",
    )

    assert result["status"] == "ready"
    assert result["classification"] == PATCH_ELIGIBLE
    assert result["fusion_candidate_id"] == "music_mitosis_fusion"
    assert len(load_arena_research_ideas(tmp_path)) == 3
    assert len(result["supporting_candidate_ids"]) >= 2
    assert result["fused_plan"]["source"] == "music_mitosis_fusion"
    assert "Council complement" in result["fused_plan"]["act_tasks"][0]["objective"]
    assert result["selected_research"]["arxiv_id"] in {"2407.01489", "2405.15793", "2509.06503"}
    assert result["diagnostics"]["covariance_shape"][0] <= 64
    assert result["diagnostics"]["feature_dimensions"] == 256


def test_high_music_score_with_zero_module_overlap_is_research_analogy(tmp_path: Path):
    _write_codemap(tmp_path)
    candidate = _candidate("planner_1", "Patch the live architect.", "Patch the grounded target.", 0.99)
    idea = {
        "idea_id": "paper-zero-overlap",
        "label": "Unrelated Paper",
        "source": "manifest",
        "target_modules": ["unrelated_module.py"],
        "implementation_lesson": "A useful but unrelated analogy.",
        "acceptance_test": "pytest test_unrelated_module.py passes.",
        "priority": 0,
    }

    result = classify_music_result(
        candidate,
        idea,
        repo_root=tmp_path,
        target_file="aura_live_architect.py",
        target_symbol="run_live_architect_transaction",
        module_overlap=0.0,
        normalized_music_score=1.0,
    )

    assert result["classification"] == RESEARCH_ANALOGY_ONLY
    assert "missing_module_overlap" in result["reasons"]
    assert "high_music_score_without_module_overlap" in result["penalties"]


def test_fake_target_symbol_blocks_music_patch_eligibility(tmp_path: Path):
    _write_codemap(tmp_path)
    candidate = _candidate("planner_1", "Patch fake symbol.", "Patch fake symbol.", 0.8)
    candidate["plan"]["target_symbol"] = "fake_symbol"
    candidate["plan"]["act_tasks"][0]["target_symbol"] = "fake_symbol"
    idea = {
        "idea_id": "paper-grounded",
        "label": "Grounded Paper",
        "source": "manifest",
        "target_modules": ["aura_live_architect.py"],
        "implementation_lesson": "Use grounded verifier evidence.",
        "acceptance_test": "pytest test_aura_live_architect.py passes.",
        "priority": 0,
    }

    result = classify_music_result(
        candidate,
        idea,
        repo_root=tmp_path,
        target_file="aura_live_architect.py",
        target_symbol="fake_symbol",
        module_overlap=1.0,
        normalized_music_score=0.8,
    )

    assert result["classification"] == BLOCKED
    assert "target_symbol_unresolved" in result["reasons"]


def test_grounded_target_with_concrete_acceptance_and_tests_is_patch_eligible(tmp_path: Path):
    _write_codemap(tmp_path)
    candidate = _candidate("planner_1", "Patch live architect.", "Patch grounded target.", 0.8)
    idea = {
        "idea_id": "paper-grounded",
        "label": "Grounded Paper",
        "source": "manifest",
        "target_modules": ["aura_live_architect.py"],
        "implementation_lesson": "Use grounded verifier evidence.",
        "acceptance_test": "pytest test_aura_live_architect.py passes.",
        "priority": 0,
    }

    result = classify_music_result(
        candidate,
        idea,
        repo_root=tmp_path,
        target_file="aura_live_architect.py",
        target_symbol="run_live_architect_transaction",
        module_overlap=1.0,
        normalized_music_score=0.8,
    )

    assert result["classification"] == PATCH_ELIGIBLE
    assert result["test_files"] == ["test_aura_live_architect.py"]
    assert result["repo_grounded_path"] is True
    assert result["acceptance_alignment"]["ok"] is True


def test_unrelated_acceptance_test_stays_research_analogy(tmp_path: Path):
    _write_codemap(tmp_path)
    candidate = _candidate("planner_1", "Patch live architect.", "Patch grounded target.", 0.8)
    idea = {
        "idea_id": "paper-grounded",
        "label": "Grounded Paper",
        "source": "manifest",
        "target_modules": ["aura_live_architect.py"],
        "implementation_lesson": "Use grounded verifier evidence.",
        "acceptance_test": "pytest test_unrelated_module.py passes.",
        "priority": 0,
    }

    result = classify_music_result(
        candidate,
        idea,
        repo_root=tmp_path,
        target_file="aura_live_architect.py",
        target_symbol="run_live_architect_transaction",
        module_overlap=1.0,
        normalized_music_score=0.8,
    )

    assert result["classification"] == RESEARCH_ANALOGY_ONLY
    assert "acceptance_not_aligned_to_target_or_verifier" in result["reasons"]
    assert result["acceptance_alignment"]["missing_test_files"] == ["test_unrelated_module.py"]


def test_rejected_scope_or_test_critics_block_patch_eligibility(tmp_path: Path):
    _write_codemap(tmp_path)
    candidate = _candidate("planner_1", "Patch live architect.", "Patch grounded target.", 0.8)
    candidate["critic_reports"] = [
        {
            "critic_id": "tests",
            "approved": False,
            "blockers": ["No verifier-facing regression test was provided."],
        }
    ]
    idea = {
        "idea_id": "paper-grounded",
        "label": "Grounded Paper",
        "source": "manifest",
        "target_modules": ["aura_live_architect.py"],
        "implementation_lesson": "Use grounded verifier evidence.",
        "acceptance_test": "pytest test_aura_live_architect.py passes.",
        "priority": 0,
    }

    result = classify_music_result(
        candidate,
        idea,
        repo_root=tmp_path,
        target_file="aura_live_architect.py",
        target_symbol="run_live_architect_transaction",
        module_overlap=1.0,
        normalized_music_score=0.8,
    )

    assert result["classification"] == BLOCKED
    assert "critic_reports_rejected_scope_or_tests" in result["blockers"]
    assert "critic_rejected_tests" in result["penalties"]


def test_vague_fused_capsule_receives_policy_penalties(tmp_path: Path):
    _write_codemap(tmp_path)
    candidate = _candidate("planner_1", "Rewrite and upgrade the whole architecture.", "Improve everything.", 0.95)
    candidate["plan"]["act_tasks"][0]["target_symbol"] = ""
    candidate["plan"]["act_tasks"][0]["allowed_scope"] = "rewrite entire new subsystem"
    idea = {
        "idea_id": "paper-grounded",
        "label": "Grounded Paper",
        "source": "manifest",
        "target_modules": ["aura_live_architect.py"],
        "implementation_lesson": "Use grounded verifier evidence.",
        "acceptance_test": "pytest test_aura_live_architect.py passes.",
        "priority": 0,
    }

    result = classify_music_result(
        candidate,
        idea,
        repo_root=tmp_path,
        target_file="aura_live_architect.py",
        target_symbol=None,
        module_overlap=1.0,
        normalized_music_score=0.9,
    )

    assert result["classification"] == BLOCKED
    assert "act_capsule_too_broad" in result["reasons"]
    assert "vague_plan" in result["penalties"]


def test_council_trace_style_music_fusion_is_blocked_before_act_capsule(tmp_path: Path):
    aura_dir = tmp_path / ".aura"
    aura_dir.mkdir()
    (tmp_path / "aura_node.py").write_text("class ExistingNode:\n    pass\n", encoding="utf-8")
    (aura_dir / "CODEMAP.json").write_text(
        json.dumps(
            {
                "coverage": {"all_included_paths_sorted": ["aura_node.py"]},
                "file_cards": [
                    {
                        "path": "aura_node.py",
                        "symbols": [{"name": "ExistingNode", "kind": "class"}],
                        "topology": {"neighbor_files": []},
                    }
                ],
                "symbol_index": {
                    "ExistingNode": [{"file": "aura_node.py", "name": "ExistingNode", "kind": "class"}],
                },
            }
        ),
        encoding="utf-8",
    )
    (aura_dir / "RESEARCH_MANIFEST.json").write_text(
        json.dumps(
            {
                "papers": [
                    {
                        "arxiv_id": "",
                        "label": "VOICE: Visual Oracle for Interaction, Conversation, and Explanation",
                        "target_modules": [],
                        "implementation_lesson": "A high-scoring but ungrounded research analogy.",
                        "acceptance_test": "Extract a concrete verifier-facing acceptance check from the paper memory before promotion.",
                        "priority": 0,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    candidates = [
        {
            "candidate_id": "planner_1",
            "source": "premium_planner",
            "score": 0.92,
            "plan": {
                "architecture_decision": "Optimize AST traversal and topology across 9123 edges.",
                "target_file": "aura_node.py",
                "target_symbol": "ASTVisitor",
                "act_tasks": [
                    {
                        "task_id": "resonance_valley_analysis",
                        "objective": "Identify critical fracture points in AST traversal through resonance valley mapping.",
                        "target_file": "aura_node.py",
                        "target_symbol": "visit_FunctionDef",
                        "acceptance": "UNIFIED_DIFF Research acceptance: Extract a concrete verifier-facing acceptance check from the paper memory before promotion.",
                        "expected_output": "UNIFIED_DIFF",
                    }
                ],
            },
        }
    ]

    result = fuse_music_council_plan(
        "find a way to make internal processes faster and token-wise",
        candidates,
        repo_root=tmp_path,
        target_file="aura_node.py",
        target_symbol="ASTVisitor",
    )

    assert result["classification"] == BLOCKED
    assert result["fusion_blocked"] is True
    assert "fused_plan" not in result
    assert result["ranked_pairs"][0]["combined_score"] <= 0.05
    grounding = result["grounding"]
    assert "target_symbol_unresolved" in grounding["blockers"]
    assert "missing_tests_or_verifier_evidence" in grounding["blockers"]
    assert "act_capsule_too_broad" in grounding["blockers"]
    assert grounding["scope"]["large_topology_terms"] == ["9123 edges"]
    assert "research_has_no_target_modules" in grounding["analogy_reasons"]
    assert "generic_research_acceptance" in grounding["analogy_reasons"]
