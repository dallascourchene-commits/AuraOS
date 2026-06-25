import asyncio
import json
from pathlib import Path

from aura_live_architect import (
    ArchitectModelRouter,
    render_live_architect_summary,
    run_live_architect_transaction,
)


def _write_codemap(root: Path) -> None:
    aura_dir = root / ".aura"
    aura_dir.mkdir()
    codemap = {
        "coverage": {
            "all_included_paths_sorted": ["demo.py", "test_demo.py"],
        },
        "file_cards": [
            {
                "path": "demo.py",
                "symbols": [{"name": "answer", "kind": "function"}],
                "topology": {"neighbor_files": ["test_demo.py"]},
            }
        ],
        "symbol_index": {
            "answer": [{"file": "demo.py", "name": "answer", "kind": "function"}],
        },
    }
    (aura_dir / "CODEMAP.json").write_text(json.dumps(codemap), encoding="utf-8")


def _write_demo_repo(root: Path) -> None:
    _write_codemap(root)
    (root / "demo.py").write_text("def answer():\n    return 1\n", encoding="utf-8")
    (root / "test_demo.py").write_text(
        "from demo import answer\n\n\ndef test_answer():\n    assert answer() == 2\n",
        encoding="utf-8",
    )
    (root / "aura_incubator.py").write_text("SENTINEL = 'unchanged'\n", encoding="utf-8")


def test_live_architect_routes_model_patch_through_temp_workspace(tmp_path: Path):
    _write_demo_repo(tmp_path)
    ledger_path = tmp_path / "Aura_Memory" / "architect_loop_ledger.jsonl"
    staging_path = tmp_path / "Aura_Staging" / "architect_live_transaction.json"

    async def model_caller(provider: str, prompt: str, meta: dict):
        if meta["role"] == "planner":
            return json.dumps(
                {
                    "architecture_decision": "Patch demo.answer through the live Architect arena.",
                    "target_file": "demo.py",
                    "target_symbol": "answer",
                    "act_tasks": [
                        {
                            "task_id": "A-LIVE-DEMO",
                            "objective": "Change demo.answer to return the verified value.",
                            "target_file": "demo.py",
                            "target_symbol": "answer",
                            "acceptance": "test_demo.py passes in the temp workspace.",
                            "expected_output": "UNIFIED_DIFF",
                        }
                    ],
                }
            )
        assert provider
        assert "Act Capsule" in prompt
        return (
            "diff --git a/demo.py b/demo.py\n"
            "--- a/demo.py\n"
            "+++ b/demo.py\n"
            "@@ -1,2 +1,2 @@\n"
            " def answer():\n"
            "-    return 1\n"
            "+    return 2\n"
        )

    transaction = asyncio.run(
        run_live_architect_transaction(
            "make demo.answer return two",
            repo_root=tmp_path,
            model_caller=model_caller,
            ledger_path=ledger_path,
            staging_path=staging_path,
        )
    )

    assert transaction.verification.hotswap_ready is True
    assert transaction.hotswap_capsule["status"] == "ready"
    assert transaction.workspace.ok is True
    assert staging_path.exists()
    assert ledger_path.exists()
    assert "unchanged" in (tmp_path / "aura_incubator.py").read_text(encoding="utf-8")
    assert "HOTSWAP READY" in render_live_architect_summary(transaction)


def test_live_architect_defaults_outputs_under_effective_repo_root(tmp_path: Path):
    _write_demo_repo(tmp_path)
    expected_ledger_path = tmp_path / "Aura_Memory" / "architect_loop_ledger.jsonl"
    expected_staging_path = tmp_path / "Aura_Staging" / "architect_live_transaction.json"

    async def model_caller(provider: str, prompt: str, meta: dict):
        if meta["role"] == "planner":
            return json.dumps(
                {
                    "architecture_decision": "Patch demo.answer through the live Architect arena.",
                    "target_file": "demo.py",
                    "target_symbol": "answer",
                    "act_tasks": [
                        {
                            "task_id": "A-LIVE-DEMO",
                            "objective": "Change demo.answer to return the verified value.",
                            "target_file": "demo.py",
                            "target_symbol": "answer",
                            "acceptance": "test_demo.py passes in the temp workspace.",
                            "expected_output": "UNIFIED_DIFF",
                        }
                    ],
                }
            )
        assert provider
        assert "Act Capsule" in prompt
        return (
            "diff --git a/demo.py b/demo.py\n"
            "--- a/demo.py\n"
            "+++ b/demo.py\n"
            "@@ -1,2 +1,2 @@\n"
            " def answer():\n"
            "-    return 1\n"
            "+    return 2\n"
        )

    transaction = asyncio.run(
        run_live_architect_transaction(
            "make demo.answer return two",
            repo_root=tmp_path,
            model_caller=model_caller,
        )
    )

    assert transaction.verification.hotswap_ready is True
    assert expected_staging_path.exists()
    assert expected_ledger_path.exists()
    assert Path(transaction.staging_path) == expected_staging_path


def test_live_architect_blocks_partial_act_stage(tmp_path: Path):
    _write_demo_repo(tmp_path)

    async def model_caller(provider: str, prompt: str, meta: dict):
        if meta["role"] == "planner":
            return json.dumps(
                {
                    "architecture_decision": "Patch demo.answer through a complete multi-Act plan.",
                    "target_file": "demo.py",
                    "target_symbol": "answer",
                    "act_tasks": [
                        {
                            "task_id": "A-LIVE-DEMO",
                            "objective": "Change demo.answer to return the verified value.",
                            "target_file": "demo.py",
                            "target_symbol": "answer",
                            "acceptance": "test_demo.py passes in the temp workspace.",
                            "expected_output": "UNIFIED_DIFF",
                        },
                        {
                            "task_id": "A-LIVE-SKIP",
                            "objective": "Confirm the same helper received the paired Act implementation.",
                            "target_file": "demo.py",
                            "target_symbol": "answer",
                            "acceptance": "A second staged patch is present for this Act Capsule.",
                            "expected_output": "UNIFIED_DIFF",
                        },
                    ],
                }
            )
        assert provider
        assert "Act Capsule" in prompt
        if meta.get("task_id") == "A-LIVE-SKIP":
            return ""
        return (
            "diff --git a/demo.py b/demo.py\n"
            "--- a/demo.py\n"
            "+++ b/demo.py\n"
            "@@ -1,2 +1,2 @@\n"
            " def answer():\n"
            "-    return 1\n"
            "+    return 2\n"
        )

    transaction = asyncio.run(
        run_live_architect_transaction(
            "make demo.answer return two with a paired Act",
            repo_root=tmp_path,
            model_caller=model_caller,
        )
    )

    act_stage_failure = next(
        item for item in transaction.verification.failures if item.get("stage") == "act_stage"
    )
    assert transaction.verification.hotswap_ready is False
    assert act_stage_failure["missing_task_ids"] == ["A-LIVE-SKIP"]


def test_live_architect_runs_fusion_council_shadow_and_judge(tmp_path: Path):
    _write_demo_repo(tmp_path)
    calls: list[tuple[str, str]] = []

    def plan(task_id: str, decision: str) -> str:
        return json.dumps(
            {
                "architecture_decision": decision,
                "target_file": "demo.py",
                "target_symbol": "answer",
                "act_tasks": [
                    {
                        "task_id": task_id,
                        "objective": "Change demo.answer to return the verified value.",
                        "target_file": "demo.py",
                        "target_symbol": "answer",
                        "acceptance": "test_demo.py passes in the temp workspace.",
                        "expected_output": "UNIFIED_DIFF",
                    }
                ],
            }
        )

    async def model_caller(provider: str, prompt: str, meta: dict):
        calls.append((meta["role"], meta.get("council_phase", "")))
        if meta["role"] == "planner":
            return plan("A-PRIMARY", "Primary premium planner candidate.")
        if meta["role"] == "planner_alt":
            return plan("A-ALT", "Alternate premium planner candidate.")
        if meta["role"] == "shadow":
            return json.dumps({"approved": True, "score": 0.91, "blockers": [], "rationale": "Scope and tests are bounded."})
        if meta["role"] == "judge" and meta.get("council_phase") == "plan_judge":
            return json.dumps({"selected_candidate_id": "planner_alt_2", "approved": True, "rationale": "Alternate plan has the cleaner boundary."})
        if meta["role"] == "judge" and meta.get("council_phase") == "patch_bundle_judge":
            return json.dumps({"approved": True, "rationale": "Patch bundle covers the selected Act Capsule."})
        assert provider
        assert meta["role"] == "worker"
        assert meta["task_id"] == "A-ALT"
        assert "Act Capsule" in prompt
        return (
            "diff --git a/demo.py b/demo.py\n"
            "--- a/demo.py\n"
            "+++ b/demo.py\n"
            "@@ -1,2 +1,2 @@\n"
            " def answer():\n"
            "-    return 1\n"
            "+    return 2\n"
        )

    transaction = asyncio.run(
        run_live_architect_transaction(
            "make demo.answer return two through a judged council",
            repo_root=tmp_path,
            model_caller=model_caller,
        )
    )

    roles = {role for role, _phase in calls}
    phases = {phase for _role, phase in calls}
    assert {"planner", "planner_alt", "shadow", "judge", "worker"} <= roles
    assert {"plan_candidate", "plan_shadow", "plan_judge", "patch_bundle_judge"} <= phases
    assert transaction.verification.hotswap_ready is True
    assert transaction.fusion_council["judge_decision"]["selected_candidate_id"] == "planner_alt_2"
    assert transaction.fusion_council["patch_judgement"]["premium_called"] is True
    assert transaction.hotswap_capsule["promotion_entrypoint"]["promote_command"] == "!stage_merge"
    assert transaction.hotswap_capsule["topology_delta"]["summary"]["files_checked"] == 1
    assert transaction.hotswap_capsule["topology_delta"]["files"][0]["calls"]["added"] == []


def test_live_architect_blocks_rejected_plan_judge_even_if_patch_judge_approves(tmp_path: Path):
    _write_demo_repo(tmp_path)

    async def model_caller(provider: str, prompt: str, meta: dict):
        if meta["role"] in {"planner", "planner_alt"}:
            return json.dumps(
                {
                    "architecture_decision": "Patch demo.answer through a council candidate.",
                    "target_file": "demo.py",
                    "target_symbol": "answer",
                    "act_tasks": [
                        {
                            "task_id": "A-REJECTED-PLAN",
                            "objective": "Change demo.answer to return the verified value.",
                            "target_file": "demo.py",
                            "target_symbol": "answer",
                            "acceptance": "test_demo.py passes in the temp workspace.",
                            "expected_output": "UNIFIED_DIFF",
                        }
                    ],
                }
            )
        if meta["role"] == "shadow":
            return json.dumps({"approved": True, "score": 0.9, "blockers": [], "rationale": "No cheap blocker."})
        if meta["role"] == "judge" and meta.get("council_phase") == "plan_judge":
            return json.dumps({"selected_candidate_id": "planner_1", "approved": False, "rationale": "Plan needs human redesign."})
        if meta["role"] == "judge" and meta.get("council_phase") == "patch_bundle_judge":
            return json.dumps({"approved": True, "rationale": "Patch itself applies."})
        assert provider
        assert "Act Capsule" in prompt
        return (
            "diff --git a/demo.py b/demo.py\n"
            "--- a/demo.py\n"
            "+++ b/demo.py\n"
            "@@ -1,2 +1,2 @@\n"
            " def answer():\n"
            "-    return 1\n"
            "+    return 2\n"
        )

    transaction = asyncio.run(
        run_live_architect_transaction(
            "make demo.answer return two but reject the plan",
            repo_root=tmp_path,
            model_caller=model_caller,
        )
    )

    assert transaction.verification.hotswap_ready is False
    assert transaction.fusion_council["judge_decision"]["approved"] is False
    assert any(item.get("stage") == "council_plan_judge" for item in transaction.verification.failures)


def test_live_architect_falls_back_to_codemap_target(tmp_path: Path):
    _write_demo_repo(tmp_path)
    router = ArchitectModelRouter(repo_root=tmp_path)
    assert router.infer_target_file("please improve the answer helper") == "demo.py"
