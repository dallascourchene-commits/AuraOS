import json
from pathlib import Path

import pytest

from aura_architect_loop import (
    ARCHITECT_LOOP_VERSION,
    PLAN_CAPSULE_VERSION,
    ArchitectFusionLoop,
    CodemapLoadError,
    append_architect_ledger,
    architect_capability_cards,
    build_fractal_plan_capsule,
    build_hotswap_capsule,
    ground_plan_capsule,
    route_intensity,
    shadow_plan_capsule,
    stage_arena_patch,
    verify_refactor_arena,
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
    assert result.grounding[0].dream_scores
    assert result.grounding[0].dream_scores[0]["target_type"] == "code_context"
    assert result.shadow_report.ok is True
    assert result.arena.ready_for_incubator is True
    assert result.arena.boundary_contracts[0]["invariant"].startswith("preserve phase_hash")
    assert result.arena.boundary_contracts[0]["contract_version"] == "AURA_BOUNDARY_CONTRACT_V1"
    assert result.arena.agent_leases[0]["capsule_id"] == "A1"
    assert result.arena.liquid_arena["domain"] == "code"
    assert result.arena.liquid_arena["action_capsules"][0]["metadata"]["dream_context_scores"]
    forbidden_actions = set(result.arena.liquid_arena["action_capsules"][0]["forbidden_actions"])
    assert {
        "mutate production files directly",
        "touch files outside leased regions",
        "write aura_incubator.py in live Architect mode",
        "invent behavior across a boundary without a BoundaryContract",
    } <= forbidden_actions
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


def test_shadow_report_blocks_legacy_incubator_target():
    plan = build_fractal_plan_capsule(
        "Try to route live Architect through the legacy incubator",
        architecture_decision="Live Architect must stage through the Refactor Arena.",
        repo_root=REPO_ROOT,
        act_tasks=[
            {
                "task_id": "A-INCUBATOR",
                "objective": "Write a generated patch to the legacy incubator.",
                "target_file": "aura_incubator.py",
            }
        ],
    )

    grounding = ground_plan_capsule(plan, repo_root=REPO_ROOT)
    report = shadow_plan_capsule(plan, grounding)

    assert report.ok is False
    assert "legacy_incubator_target" in {finding.shadow_type for finding in report.findings}


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


def test_architect_capability_cards_cover_final_loop():
    cards = architect_capability_cards()
    assert [card["capability"] for card in cards] == [
        "plan",
        "act",
        "ground",
        "shadow",
        "verify",
        "escalate",
        "handoff",
        "judge",
        "hotswap",
        "rollback",
        "ledger",
    ]
    assert {card["function"] for card in cards} >= {
        "build_fractal_plan_capsule",
        "stage_arena_patch",
        "verify_refactor_arena",
        "build_hotswap_capsule",
        "append_architect_ledger",
    }


def test_refactor_arena_stages_only_assigned_patch_scope():
    result = ArchitectFusionLoop(repo_root=REPO_ROOT).prepare(
        "Stage a bounded Architect patch",
        architecture_decision="Builder patches must stay inside their Act Capsule scope.",
        target_file="aura_fusion.py",
        target_symbol="build_task_capsule",
        act_tasks=[
            {
                "task_id": "A-STAGE",
                "objective": "Patch only the fusion capsule helper.",
                "target_file": "aura_fusion.py",
                "target_symbol": "build_task_capsule",
            }
        ],
    )

    staged = stage_arena_patch(
        result.arena,
        task_id="A-STAGE",
        owner="cheap_builder",
        diff="diff --git a/aura_fusion.py b/aura_fusion.py\n--- a/aura_fusion.py\n+++ b/aura_fusion.py\n",
        affected_files=["aura_fusion.py"],
        affected_symbols=["build_task_capsule"],
        tests=["test_aura_fusion.py"],
    )
    blocked = stage_arena_patch(
        result.arena,
        task_id="A-STAGE",
        owner="cheap_builder",
        diff="diff --git a/README.md b/README.md\n--- a/README.md\n+++ b/README.md\n",
        affected_files=["README.md"],
    )

    assert staged.ok is True
    assert staged.patch is not None
    assert result.arena.shared_patch_queue[0]["patch_id"] == staged.patch.patch_id
    assert result.arena.liquid_arena["shared_action_queue"][0]["action_type"] == "patch_staged"
    assert result.arena.liquid_arena["shared_action_queue"][0]["patch_id"] == staged.patch.patch_id
    assert blocked.ok is False
    assert {finding.shadow_type for finding in blocked.findings} >= {"cross_boundary_patch", "lease_scope_violation"}


def test_refactor_arena_rejects_diff_paths_that_do_not_match_metadata():
    result = ArchitectFusionLoop(repo_root=REPO_ROOT).prepare(
        "Reject dishonest Architect patch metadata",
        architecture_decision="Verifier must parse diff headers, not just trust affected_files.",
        target_file="aura_fusion.py",
        target_symbol="build_task_capsule",
        act_tasks=[
            {
                "task_id": "A-DIFF-PATH",
                "objective": "Patch only the fusion capsule helper.",
                "target_file": "aura_fusion.py",
                "target_symbol": "build_task_capsule",
            }
        ],
    )

    staged = stage_arena_patch(
        result.arena,
        task_id="A-DIFF-PATH",
        owner="cheap_builder",
        diff="diff --git a/README.md b/README.md\n--- a/README.md\n+++ b/README.md\n",
        affected_files=["aura_fusion.py"],
        tests=["test_aura_fusion.py"],
    )
    result.arena.shared_patch_queue.append(
        {
            "patch_id": "manual-lie",
            "task_id": "A-DIFF-PATH",
            "owner": "cheap_builder",
            "diff": "diff --git a/README.md b/README.md\n--- a/README.md\n+++ b/README.md\n",
            "affected_files": ["aura_fusion.py"],
            "status": "staged",
            "tests": ["test_aura_fusion.py"],
        }
    )
    verified = verify_refactor_arena(
        result.arena,
        repo_root=REPO_ROOT,
        runner=lambda test_name: {"status": "passed", "test": test_name},
    )

    assert staged.ok is False
    assert {finding.shadow_type for finding in staged.findings} >= {"undeclared_diff_file"}
    assert verified.hotswap_ready is False
    assert any(failure["stage"] == "patch_diff_files" for failure in verified.failures)


def test_verifier_blocks_until_tests_run_then_builds_hotswap_capsule():
    result = ArchitectFusionLoop(repo_root=REPO_ROOT).prepare(
        "Verify a staged Architect patch",
        architecture_decision="Hot-swap must wait for verifier-owned tests.",
        target_file="aura_fusion.py",
        target_symbol="build_task_capsule",
        act_tasks=[
            {
                "task_id": "A-VERIFY",
                "objective": "Patch only the fusion capsule helper.",
                "target_file": "aura_fusion.py",
                "target_symbol": "build_task_capsule",
            }
        ],
    )
    stage_arena_patch(
        result.arena,
        task_id="A-VERIFY",
        owner="cheap_builder",
        diff="diff --git a/aura_fusion.py b/aura_fusion.py\n--- a/aura_fusion.py\n+++ b/aura_fusion.py\n",
        affected_files=["aura_fusion.py"],
        tests=["test_aura_fusion.py"],
    )

    pending = verify_refactor_arena(result.arena, repo_root=REPO_ROOT)
    verified = verify_refactor_arena(
        result.arena,
        repo_root=REPO_ROOT,
        runner=lambda test_name: {"status": "passed", "test": test_name},
    )
    capsule = build_hotswap_capsule(result.arena, verified, repo_root=REPO_ROOT)

    assert pending.hotswap_ready is False
    assert any(failure["stage"] == "tests" for failure in pending.failures)
    assert verified.hotswap_ready is True
    assert capsule["status"] == "ready"
    assert capsule["judge"]["decision"] == "promote_hotswap"
    assert capsule["liquid_arena"]["domain"] == "code"
    assert capsule["liquid_arena"]["lease_count"] == 1
    assert capsule["liquid_arena"]["shared_action_count"] == 1
    assert capsule["rollback_capsule"]["files"][0]["path"] == "aura_fusion.py"


def test_architect_execute_appends_ledger_record(tmp_path: Path):
    ledger_path = tmp_path / "architect_loop.jsonl"
    execution = ArchitectFusionLoop(repo_root=REPO_ROOT).execute(
        "Execute a complete Architect transaction",
        architecture_decision="Stage, verify, hot-swap, and ledger the bounded patch.",
        target_file="aura_fusion.py",
        target_symbol="build_task_capsule",
        act_tasks=[
            {
                "task_id": "A-LEDGER",
                "objective": "Patch only the fusion capsule helper.",
                "target_file": "aura_fusion.py",
                "target_symbol": "build_task_capsule",
            }
        ],
        patch_submissions=[
            {
                "task_id": "A-LEDGER",
                "owner": "cheap_builder",
                "diff": "diff --git a/aura_fusion.py b/aura_fusion.py\n--- a/aura_fusion.py\n+++ b/aura_fusion.py\n",
                "affected_files": ["aura_fusion.py"],
                "tests": ["test_aura_fusion.py"],
            }
        ],
        runner=lambda test_name: {"status": "passed", "test": test_name},
        ledger_path=ledger_path,
    )
    rows = [line for line in ledger_path.read_text(encoding="utf-8").splitlines() if line]

    assert execution.verification.hotswap_ready is True
    assert execution.hotswap_capsule["status"] == "ready"
    assert len(rows) == 1
    assert json.loads(rows[0])["phase_hash"] == execution.ledger_record.phase_hash


def test_append_architect_ledger_accepts_dict_payload(tmp_path: Path):
    ledger_path = tmp_path / "manual.jsonl"
    append_architect_ledger({"event": "manual", "phase_hash": "abc123"}, ledger_path=ledger_path)
    assert ledger_path.read_text(encoding="utf-8").strip() == '{"event": "manual", "phase_hash": "abc123"}'
