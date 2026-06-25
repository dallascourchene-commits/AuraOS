from pathlib import Path

import pytest

from aura_architect_loop import (
    ARCHITECT_LOOP_VERSION,
    ArchitectFusionLoop,
    CodemapLoadError,
    PLAN_CAPSULE_VERSION,
    build_fractal_plan_capsule,
    ground_plan_capsule,
    route_intensity,
    shadow_plan_capsule,
)


REPO_ROOT = Path(__file__).resolve().parent


def test_architect_loop_builds_grounded_plan_act_arena():
    loop = ArchitectFusionLoop(repo_root=REPO_ROOT)
    result = loop.prepare(
        "Wrap Architect in a grounded Plan/Act loop",
        architecture_decision="Use deterministic sharded Act Capsules before Builder execution.",
        target_file="aura_fusion.py",
        target_symbol="build_task_capsule",
        act_tasks=[
            {
                "task_id": "A1",
                "objective": "Extend Fusion capsule metadata without changing public signatures.",
                "target_file": "aura_fusion.py",
                "target_symbol": "build_task_capsule",
                "allowed_scope": "single helper-level edit",
                "acceptance": "Existing Fusion tests still pass.",
            }
        ],
        acceptance_criteria=["Act Capsule is CODEMAP-grounded before Builder runs."],
    )

    assert result.plan.capsule_version == PLAN_CAPSULE_VERSION
    assert result.plan.fusion_capsule["architect_loop_version"] == ARCHITECT_LOOP_VERSION
    assert result.plan.context_ref.startswith("ST3GG-L2::PLAN:")
    assert result.plan.act_capsules[0].context_ref.startswith("ST3GG-L2::ACT:")
    assert result.plan.act_capsules[0].size == "S"
    assert result.grounding[0].file_exists is True
    assert result.grounding[0].codemap_file_hit is True
    assert result.grounding[0].symbol_exists is True
    assert result.grounding[0].test_files == ["test_aura_fusion.py"]
    assert result.shadow_report.ok is True
    assert result.arena.ready_for_incubator is True
    assert result.arena.boundary_contracts[0]["invariant"].startswith("preserve phase_hash")
    assert result.intensity == 1


def test_shadow_report_blocks_fake_file_and_symbol():
    plan = build_fractal_plan_capsule(
        "Try an ungrounded refactor",
        architecture_decision="This should be blocked by local truth checks.",
        repo_root=REPO_ROOT,
        act_tasks=[
            {
                "task_id": "A404",
                "objective": "Patch a module that does not exist.",
                "target_file": "aura_missing_architect.py",
                "target_symbol": "MissingArchitect",
            }
        ],
    )

    grounding = ground_plan_capsule(plan, repo_root=REPO_ROOT)
    report = shadow_plan_capsule(plan, grounding)

    shadow_types = {finding.shadow_type for finding in report.findings}
    assert report.ok is False
    assert "fake_file" in shadow_types
    assert "fake_symbol" in shadow_types
    assert report.gate == "BLOCK_BUILDER"
    assert route_intensity(plan, report) == 4


def test_grounder_fails_closed_without_codemap(tmp_path: Path):
    (tmp_path / "aura_fusion.py").write_text("# local file without CODEMAP\n", encoding="utf-8")
    plan = build_fractal_plan_capsule(
        "Try to ground without a CODEMAP artifact",
        architecture_decision="Grounder must fail closed when CODEMAP is unavailable.",
        repo_root=tmp_path,
        act_tasks=[
            {
                "task_id": "A-CODEMAP",
                "objective": "Patch an existing file in a repo with no CODEMAP.",
                "target_file": "aura_fusion.py",
            }
        ],
    )

    with pytest.raises(CodemapLoadError, match="Cannot ground Architect plan without CODEMAP"):
        ground_plan_capsule(plan, repo_root=tmp_path)


def test_shadow_report_blocks_out_of_repo_existing_file(tmp_path: Path):
    outside = tmp_path / "outside.py"
    outside.write_text("# outside repo boundary\n", encoding="utf-8")
    plan = build_fractal_plan_capsule(
        "Try an out-of-repo target",
        architecture_decision="Resolved targets must stay inside repo_root.",
        repo_root=REPO_ROOT,
        act_tasks=[
            {
                "task_id": "A-OUT",
                "objective": "Patch a file outside the Aura repo.",
                "target_file": str(outside),
            }
        ],
    )

    grounding = ground_plan_capsule(plan, repo_root=REPO_ROOT)
    report = shadow_plan_capsule(plan, grounding)

    assert grounding[0].file_exists is False
    assert grounding[0].codemap_file_hit is False
    assert report.ok is False
    assert {finding.shadow_type for finding in report.findings} >= {"fake_file"}


def test_high_context_pressure_attaches_phase_continuity_capsule():
    result = ArchitectFusionLoop(repo_root=REPO_ROOT).prepare(
        "Preserve Architect continuity across context rollover",
        architecture_decision="Emit a phase capsule when context pressure crosses the handoff threshold.",
        target_file="aura_phase_capsule.py",
        target_symbol="capture_phase_capsule",
        context_pressure=0.91,
        act_tasks=[
            {
                "task_id": "A2",
                "objective": "Verify rollover metadata keeps target file and phase hash stable.",
                "target_file": "aura_phase_capsule.py",
                "target_symbol": "capture_phase_capsule",
                "acceptance": "Phase capsule resume metadata names the same target.",
            }
        ],
    )

    continuity = result.plan.continuity_capsule
    assert continuity is not None
    assert continuity.next_role == "WORKER"
    assert continuity.target_file == "aura_phase_capsule.py"
    assert continuity.target_symbol == "capture_phase_capsule"
    assert len(continuity.phase_hash) == 32
