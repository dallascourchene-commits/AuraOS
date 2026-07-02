import asyncio
import json
from pathlib import Path

from aura_live_architect import run_live_architect_transaction


def _write_demo_repo(root: Path) -> None:
    aura_dir = root / ".aura"
    aura_dir.mkdir()
    (aura_dir / "CODEMAP.json").write_text(
        json.dumps(
            {
                "coverage": {"all_included_paths_sorted": ["demo.py", "test_demo.py"]},
                "files": [
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
        ),
        encoding="utf-8",
    )
    (root / "demo.py").write_text("def answer():\n    return 1\n", encoding="utf-8")
    (root / "test_demo.py").write_text("from demo import answer\n", encoding="utf-8")


def test_failed_live_architect_preserves_reviewable_worker_output(tmp_path: Path):
    _write_demo_repo(tmp_path)
    staging_path = tmp_path / "Aura_Staging" / "architect_live_transaction.json"
    worker_diff = (
        "diff --git a/demo.py b/demo.py\n"
        "--- a/demo.py\n"
        "+++ b/demo.py\n"
        "@@ -1,2 +1,2 @@\n"
        " def answer():\n"
        "-    return 1\n"
        "+    return 2\n"
    )

    async def model_caller(provider: str, prompt: str, meta: dict):
        if meta.get("role") == "planner":
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
        if meta.get("repair_phase") == "PATCH_FORMAT_REPAIR":
            return worker_diff
        if meta.get("role") == "judge":
            return json.dumps({"approved": True, "rationale": "Review failed worker output."})
        if meta.get("role") == "shadow":
            return json.dumps({"approved": True, "score": 0.9, "blockers": []})
        return worker_diff

    transaction = asyncio.run(
        run_live_architect_transaction(
            "make demo.answer return two",
            repo_root=tmp_path,
            model_caller=model_caller,
            staging_path=staging_path,
        )
    )

    assert transaction.verification.hotswap_ready is False
    attempt = transaction.patch_quality["attempts"][0]
    assert attempt["raw_model_response"] == worker_diff
    assert attempt["extracted_diff"] == worker_diff
    assert attempt["repair"]["candidate_diff"] == worker_diff.strip()
    assert attempt["builder_context"]["target_file"] == "demo.py"

    saved = json.loads(staging_path.read_text(encoding="utf-8"))
    saved_attempt = saved["patch_quality"]["review_artifacts"][0]
    assert saved_attempt["raw_model_response"] == worker_diff
    assert saved_attempt["repair"]["candidate_diff"] == worker_diff.strip()
