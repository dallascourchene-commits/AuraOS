import asyncio
import json
from pathlib import Path

from aura_builder_context import build_builder_context_packet
from aura_coding_arena_grounding import (
    ground_coding_arena_intent,
    query_coding_arena_external_calls,
)
from aura_live_architect import run_live_architect_transaction


def _write_codemap(root: Path) -> None:
    aura_dir = root / ".aura"
    aura_dir.mkdir()
    codemap = {
        "coverage": {"all_included_paths_sorted": ["demo.py", "test_demo.py"]},
        "file_cards": [
            {
                "path": "demo.py",
                "symbols": [{"name": "answer", "kind": "function", "line": 1, "end_line": 2}],
                "topology": {"neighbor_files": ["test_demo.py"]},
            }
        ],
        "symbol_index": {
            "answer": [{"file": "demo.py", "name": "answer", "kind": "function", "line": 1, "end_line": 2}],
        },
    }
    (aura_dir / "CODEMAP.json").write_text(json.dumps(codemap), encoding="utf-8")


def _write_demo_repo(root: Path, *, with_tests: bool = True) -> None:
    _write_codemap(root)
    (root / "demo.py").write_text("def answer():\n    return 1\n", encoding="utf-8")
    if with_tests:
        (root / "test_demo.py").write_text(
            "from demo import answer\n\n\ndef test_answer():\n    assert answer() == 1\n",
            encoding="utf-8",
        )


def test_coding_arena_grounding_reports_requests_get_external_call(tmp_path: Path):
    (tmp_path / "client.py").write_text(
        "import requests as rq\n\n\ndef fetch():\n    return rq.get('https://example.test')\n",
        encoding="utf-8",
    )

    packet = ground_coding_arena_intent(
        "where is requests.get used",
        tmp_path,
        external_call="requests.get",
    )

    assert packet["route"] == "EXTERNAL_CALL_CONTEXT"
    call = packet["external_calls"][0]
    assert call["resolved_call"] == "requests.get"
    assert call["call"] == "rq.get"
    assert call["caller_symbol"] == "fetch"
    assert call["file_path"] == "client.py"
    assert call["line"] == 5
    assert call["caller_span"] == [4, 5]
    assert call["source_hash"]


def test_empty_external_call_query_returns_all_known_external_calls(tmp_path: Path):
    (tmp_path / "client.py").write_text(
        "\n".join(
            [
                "import httpx",
                "import subprocess",
                "from openai import OpenAI",
                "",
                "def run():",
                "    client = OpenAI()",
                "    httpx.get('https://example.test')",
                "    return subprocess.run(['echo', 'ok'])",
            ]
        ),
        encoding="utf-8",
    )

    packet = query_coding_arena_external_calls("", tmp_path)

    resolved = {call["resolved_call"] for call in packet["external_calls"]}
    assert {"openai.OpenAI", "httpx.get", "subprocess.run"} <= resolved
    assert packet["route"] == "EXTERNAL_CALL_CONTEXT"


def test_grounded_symbol_with_tests_routes_to_builder_patch(tmp_path: Path):
    _write_demo_repo(tmp_path, with_tests=True)

    packet = ground_coding_arena_intent("patch answer", tmp_path, target_symbol="answer")

    assert packet["route"] == "BUILDER_PATCH"
    assert packet["target_file"] == "demo.py"
    assert packet["target_symbol"] == "answer"
    assert packet["tests"] == ["test_demo.py"]
    assert packet["source_spans"][0]["source_hash"]


def test_grounded_symbol_without_tests_routes_to_test_gap_fill(tmp_path: Path):
    _write_demo_repo(tmp_path, with_tests=False)

    packet = ground_coding_arena_intent("patch answer", tmp_path, target_symbol="answer")

    assert packet["route"] == "TEST_GAP_FILL"
    assert packet["exact_hits"]
    assert packet["tests"] == []


def test_fake_symbol_routes_to_localize_first_without_builder_patch(tmp_path: Path):
    _write_demo_repo(tmp_path, with_tests=True)

    packet = ground_coding_arena_intent("patch missing symbol", tmp_path, target_symbol="missing_symbol")

    assert packet["route"] == "LOCALIZE_FIRST"
    assert packet["exact_hits"] == []
    assert packet["route"] != "BUILDER_PATCH"


def test_syntax_error_file_blocks_unsafe_grounding(tmp_path: Path):
    (tmp_path / "broken.py").write_text("def bad(:\n    pass\n", encoding="utf-8")

    packet = ground_coding_arena_intent("patch bad", tmp_path, target_symbol="bad")

    assert packet["route"] == "BLOCKED_WITH_REASON"
    assert any("syntax_error:broken.py" in warning for warning in packet["warnings"])


def test_no_staged_patch_records_agentless_fallback_without_second_model_debate(tmp_path: Path):
    _write_demo_repo(tmp_path, with_tests=True)
    roles: list[str] = []

    def plan() -> str:
        return json.dumps(
            {
                "architecture_decision": "Patch demo.answer through the live Architect arena.",
                "target_file": "demo.py",
                "target_symbol": "answer",
                "act_tasks": [
                    {
                        "task_id": "A-NO-PATCH",
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
        roles.append(meta["role"])
        if meta["role"] in {"planner", "planner_alt"}:
            return plan()
        if meta["role"] == "shadow":
            return json.dumps({"approved": True, "score": 0.9, "blockers": [], "rationale": "Grounded."})
        if meta["role"] == "judge":
            return json.dumps({"approved": True, "selected_candidate_id": "planner_1", "rationale": "Accept."})
        assert meta["role"] == "worker"
        return ""

    transaction = asyncio.run(
        run_live_architect_transaction(
            "make demo.answer return two but worker refuses",
            repo_root=tmp_path,
            model_caller=model_caller,
        )
    )

    fallback = transaction.patch_quality["agentless_fallback"]
    assert fallback["ok"] is True
    assert len(fallback["localized_files"]) <= 5
    worker_index = max(index for index, role in enumerate(roles) if role == "worker")
    assert roles[worker_index + 1 :] == []


def test_builder_context_renders_topological_anchor_policy_and_hashes(tmp_path: Path):
    _write_demo_repo(tmp_path, with_tests=True)
    codemap = json.loads((tmp_path / ".aura" / "CODEMAP.json").read_text(encoding="utf-8"))
    grounding = {
        "codemap_symbol_hits": [{"file": "demo.py", "name": "answer", "line": 1, "end_line": 2}],
        "test_files": ["test_demo.py"],
        "neighbor_files": ["test_demo.py"],
    }

    packet = build_builder_context_packet(
        target_file="demo.py",
        target_symbol="answer",
        grounding_evidence=grounding,
        codemap=codemap,
        repo_root=tmp_path,
        objective="patch answer",
        task_id="A1",
    )

    prompt = packet.to_prompt_section()
    assert "TOPOLOGICAL CONTEXT ANCHOR" in prompt
    assert "exact_span: demo.py:1-2 symbol=answer" in prompt
    assert "source_hash=" in prompt
    assert "vsa_similarity: advisory ranking only; never patch evidence" in prompt
