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


def test_live_architect_falls_back_to_codemap_target(tmp_path: Path):
    _write_demo_repo(tmp_path)
    router = ArchitectModelRouter(repo_root=tmp_path)
    assert router.infer_target_file("please improve the answer helper") == "demo.py"
