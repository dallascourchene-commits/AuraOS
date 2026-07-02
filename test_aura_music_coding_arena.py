import json
from pathlib import Path

from aura_music_coding_arena import fuse_music_council_plan, load_arena_research_ideas


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
    assert result["fusion_candidate_id"] == "music_mitosis_fusion"
    assert len(load_arena_research_ideas(tmp_path)) == 3
    assert len(result["supporting_candidate_ids"]) >= 2
    assert result["fused_plan"]["source"] == "music_mitosis_fusion"
    assert "Council complement" in result["fused_plan"]["act_tasks"][0]["objective"]
    assert result["selected_research"]["arxiv_id"] in {"2407.01489", "2405.15793", "2509.06503"}
    assert result["diagnostics"]["covariance_shape"][0] <= 64
    assert result["diagnostics"]["feature_dimensions"] == 256
