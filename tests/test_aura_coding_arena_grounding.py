import asyncio
import json
from pathlib import Path

from aura_builder_context import build_builder_context_packet
from aura_coding_arena_grounding import (
    ground_coding_arena_intent,
    query_coding_arena_capability_audit,
    query_coding_arena_external_calls,
)
from aura_live_architect import (
    ArchitectBuilderBridge,
    ArchitectFusionLoop,
    ArchitectModelRouter,
    run_live_architect_transaction,
)


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


def _prepared_for_grounding(root: Path, topological_grounding: dict, *, target_symbol: str = "answer"):
    loop = ArchitectFusionLoop(repo_root=root)
    return loop.prepare(
        "patch answer",
        architecture_decision="Patch demo.answer through the live Architect arena.",
        target_file="demo.py",
        target_symbol=target_symbol,
        act_tasks=[
            {
                "task_id": "A-GROUNDING",
                "objective": "Patch demo.answer with bounded output.",
                "target_file": "demo.py",
                "target_symbol": target_symbol,
                "acceptance": "test_demo.py passes.",
                "expected_output": "UNIFIED_DIFF",
                "topological_grounding": topological_grounding,
            }
        ],
        acceptance_criteria=["Patch applies."],
        rollback_conditions=["Builder blocked."],
        risk_map=["Grounding route is non-patch."],
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
    assert packet["jspace_route"]["next_state"] == "READ_ONLY_CONTEXT"


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
    assert packet["jspace_route"]["next_state"] == "READY_PATCH"
    assert packet["jspace_route"]["vsa_patch_authority"] is False


def test_grounded_symbol_without_tests_routes_to_test_gap_fill(tmp_path: Path):
    _write_demo_repo(tmp_path, with_tests=False)

    packet = ground_coding_arena_intent("patch answer", tmp_path, target_symbol="answer")

    assert packet["route"] == "TEST_GAP_FILL"
    assert packet["exact_hits"]
    assert packet["tests"] == []
    assert packet["jspace_route"]["next_state"] == "NEED_TEST"


def test_fake_symbol_routes_to_localize_first_without_builder_patch(tmp_path: Path):
    _write_demo_repo(tmp_path, with_tests=True)

    packet = ground_coding_arena_intent("patch missing symbol", tmp_path, target_symbol="missing_symbol")

    assert packet["route"] == "LOCALIZE_FIRST"
    assert packet["exact_hits"] == []
    assert packet["route"] != "BUILDER_PATCH"


def test_capability_audit_query_routes_to_read_only_report(tmp_path: Path):
    (tmp_path / "aura_st3gg_codec.py").write_text("def encode_st3gg_token():\n    return 'st3gg'\n", encoding="utf-8")
    (tmp_path / "aura_topological_context_anchor.py").write_text(
        "def render_topological_context():\n    return 'source_hash'\n",
        encoding="utf-8",
    )

    packet = ground_coding_arena_intent("show emergent capability audit for all", tmp_path)

    assert packet["route"] == "EMERGENT_CAPABILITY_AUDIT"
    assert packet["safe_to_patch"] is False
    assert packet["target_file"] is None
    assert packet["rendered"].startswith("# Emergent Properties and Future Potential")
    assert packet["report"]["safe_to_patch"] is False
    assert packet["report"]["summary"]["read_only"] is True
    assert packet["jspace_route"]["next_state"] == "READ_ONLY_AUDIT"


def test_capability_patch_intent_does_not_route_to_audit(tmp_path: Path):
    _write_demo_repo(tmp_path, with_tests=True)

    packet = ground_coding_arena_intent("implement emergent capability auditor", tmp_path)

    assert packet["route"] != "EMERGENT_CAPABILITY_AUDIT"


def test_api_patch_intent_does_not_route_to_external_call_context(tmp_path: Path):
    _write_demo_repo(tmp_path, with_tests=True)

    packet = ground_coding_arena_intent("fix API endpoint issue", tmp_path, target_symbol="answer")

    assert packet["route"] != "EXTERNAL_CALL_CONTEXT"
    assert packet["route"] in {"BUILDER_PATCH", "TEST_GAP_FILL", "LOCALIZE_FIRST"}


def test_direct_capability_audit_query_returns_emergent_potential_shape(tmp_path: Path):
    (tmp_path / "aura_music_coding_arena.py").write_text(
        "def rank_music_candidates():\n    return 'music resonance ranking'\n",
        encoding="utf-8",
    )
    (tmp_path / "aura_builder_context.py").write_text(
        "def build_builder_context_packet():\n    return 'builder_context packet'\n",
        encoding="utf-8",
    )

    packet = query_coding_arena_capability_audit("audit capability wiring for music", tmp_path)

    assert packet["route"] == "EMERGENT_CAPABILITY_AUDIT"
    assert packet["report"]["version"] == "AURA_EMERGENT_POTENTIAL_REPL_V1"
    assert packet["report"]["summary"]["read_only"] is True
    assert packet["safe_to_patch"] is False


def test_syntax_error_file_blocks_unsafe_grounding(tmp_path: Path):
    (tmp_path / "broken.py").write_text("def bad(:\n    pass\n", encoding="utf-8")

    packet = ground_coding_arena_intent("patch bad", tmp_path, target_symbol="bad")

    assert packet["route"] == "BLOCKED_WITH_REASON"
    assert any("syntax_error:broken.py" in warning for warning in packet["warnings"])
    assert packet["jspace_route"]["next_state"] == "BLOCKED"


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


def test_external_call_context_attempt_is_reviewable_not_patch_staged(tmp_path: Path):
    aura_dir = tmp_path / ".aura"
    aura_dir.mkdir()
    (aura_dir / "CODEMAP.json").write_text(
        json.dumps(
            {
                "coverage": {"all_included_paths_sorted": ["client.py"]},
                "file_cards": [
                    {
                        "path": "client.py",
                        "symbols": [{"name": "fetch", "kind": "function", "line": 4, "end_line": 5}],
                    }
                ],
                "symbol_index": {
                    "fetch": [{"file": "client.py", "name": "fetch", "kind": "function", "line": 4, "end_line": 5}],
                },
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "client.py").write_text(
        "import requests as rq\n\n\ndef fetch():\n    return rq.get('https://example.test')\n",
        encoding="utf-8",
    )
    roles: list[str] = []

    async def model_caller(provider: str, prompt: str, meta: dict):
        roles.append(meta["role"])
        if meta["role"] in {"planner", "planner_alt"}:
            return json.dumps(
                {
                    "architecture_decision": "Report external call context without a Builder patch.",
                    "target_file": "client.py",
                    "target_symbol": "fetch",
                    "act_tasks": [
                        {
                            "task_id": "A-EXTERNAL",
                            "objective": "Report where requests.get is used.",
                            "target_file": "client.py",
                            "target_symbol": "fetch",
                            "acceptance": "No patch is staged.",
                            "expected_output": "UNIFIED_DIFF",
                        }
                    ],
                }
            )
        if meta["role"] == "shadow":
            return json.dumps({"approved": True, "score": 0.9, "blockers": [], "rationale": "Read-only route."})
        if meta["role"] == "judge":
            return json.dumps({"approved": True, "selected_candidate_id": "planner_1", "rationale": "Accept."})
        raise AssertionError("worker should not be called for EXTERNAL_CALL_CONTEXT")

    transaction = asyncio.run(
        run_live_architect_transaction(
            "where is requests.get used",
            repo_root=tmp_path,
            model_caller=model_caller,
        )
    )

    assert "worker" not in roles
    assert transaction.stage_results == []
    assert transaction.patch_quality["patchable_submission_count"] == 0
    assert transaction.patch_quality["agentless_fallback"] is not None
    assert "ok" in transaction.patch_quality["agentless_fallback"]
    failure = transaction.patch_quality["builder_failures"][0]
    assert failure["status"] == "external_call_context"
    assert "external_call_context" in failure["reason_codes"]


def test_blocked_grounding_attempt_never_becomes_patch_submission(tmp_path: Path):
    _write_demo_repo(tmp_path, with_tests=True)
    grounding = {
        "route": "BLOCKED_WITH_REASON",
        "route_reasons": ["unsafe_parse_diagnostics"],
        "route_diagnostics": {"route": "BLOCKED_WITH_REASON", "reasons": ["unsafe_parse_diagnostics"]},
        "safety_policy": "exact_source_spans_and_hashes_only",
    }
    prepared = _prepared_for_grounding(tmp_path, grounding)
    bridge = ArchitectBuilderBridge(ArchitectModelRouter(repo_root=tmp_path))

    submissions = asyncio.run(bridge.build_patch_submissions(prepared, objective="patch answer"))

    assert submissions == []
    assert bridge.patch_quality["no_patch_staged"] is True
    attempt = bridge.patch_quality["attempts"][0]
    assert attempt["status"] == "topological_grounding_blocked"
    assert attempt["failure_reason"]["act_topological_grounding"]["route"] == "BLOCKED_WITH_REASON"


def test_test_gap_fill_route_is_reviewable_not_normal_builder_patch(tmp_path: Path):
    _write_demo_repo(tmp_path, with_tests=True)
    grounding = {
        "route": "TEST_GAP_FILL",
        "tests": [],
        "source_spans": [{"file_path": "demo.py", "symbol": "answer", "start_line": 1, "end_line": 2, "source_hash": "abc"}],
        "route_diagnostics": {"route": "TEST_GAP_FILL", "reasons": ["missing_tests_or_verifier_evidence"]},
        "safety_policy": "exact_source_spans_and_hashes_only",
    }
    prepared = _prepared_for_grounding(tmp_path, grounding)
    bridge = ArchitectBuilderBridge(ArchitectModelRouter(repo_root=tmp_path))

    submissions = asyncio.run(bridge.build_patch_submissions(prepared, objective="patch answer"))

    assert submissions == []
    assert bridge.patch_quality["attempts"][0]["status"] == "test_gap_fill_required"
    assert "test_gap_fill_required" in bridge.patch_quality["builder_failures"][0]["reason_codes"]


def test_worker_prose_without_diff_is_reviewable_not_patch_submission(tmp_path: Path):
    _write_demo_repo(tmp_path, with_tests=True)
    grounding = ground_coding_arena_intent("patch answer", tmp_path, target_symbol="answer")
    prepared = _prepared_for_grounding(tmp_path, grounding)
    worker_called = False

    async def model_caller(provider: str, prompt: str, meta: dict):
        nonlocal worker_called
        worker_called = True
        assert "VSA similarity advisory only." in prompt
        return "I can explain the change, but I am not returning a diff."

    bridge = ArchitectBuilderBridge(ArchitectModelRouter(repo_root=tmp_path, model_caller=model_caller))

    submissions = asyncio.run(bridge.build_patch_submissions(prepared, objective="patch answer"))

    assert worker_called is True
    assert submissions == []
    attempt = bridge.patch_quality["attempts"][0]
    assert attempt["status"] == "missing_patch_diff"
    assert attempt["extracted_diff"].strip()
    assert "missing_patch_diff" in attempt["failure_reason"]["reason_codes"]


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
        topological_grounding=ground_coding_arena_intent("patch answer", tmp_path, target_symbol="answer"),
    )

    prompt = packet.to_prompt_section()
    assert "TOPOLOGICAL CONTEXT ANCHOR" in prompt
    assert "exact_span: demo.py:1-2 symbol=answer" in prompt
    assert "source_hash=" in prompt
    assert "vsa_similarity: advisory ranking only; never patch evidence" in prompt
    assert "VSA similarity advisory only." in prompt
    assert "aura_jspace_route (advisory routing state; not patch authority)" in prompt
    assert prompt.index("source_excerpt") < prompt.index("aura_jspace_route")
    assert packet.topological_context["preplanning_grounding"]["route"] == "BUILDER_PATCH"
    assert packet.topological_context["jspace_route"]["next_state"] == "READY_PATCH"


def test_builder_context_preserves_route_diagnostics_from_preplanning_packet(tmp_path: Path):
    _write_demo_repo(tmp_path, with_tests=True)
    codemap = json.loads((tmp_path / ".aura" / "CODEMAP.json").read_text(encoding="utf-8"))
    grounding = {
        "codemap_symbol_hits": [{"file": "demo.py", "name": "answer", "line": 1, "end_line": 2}],
        "test_files": ["test_demo.py"],
        "neighbor_files": ["test_demo.py"],
    }
    topological_grounding = ground_coding_arena_intent("patch answer", tmp_path, target_symbol="answer")

    packet = build_builder_context_packet(
        target_file="demo.py",
        target_symbol="answer",
        grounding_evidence=grounding,
        codemap=codemap,
        repo_root=tmp_path,
        objective="patch answer",
        task_id="A1",
        topological_grounding=topological_grounding,
    )

    assert packet.topological_context["packet"]["route_diagnostics"]["route"] == "BUILDER_PATCH"
    assert packet.topological_context["packet"]["preplanning_route_diagnostics"]["route"] == "BUILDER_PATCH"


def test_patch_grounding_eligibility_reads_route_diagnostics_from_packet(tmp_path: Path):
    _write_demo_repo(tmp_path, with_tests=True)
    grounding = ground_coding_arena_intent("patch answer", tmp_path, target_symbol="answer")
    prepared = _prepared_for_grounding(tmp_path, grounding)
    bridge = ArchitectBuilderBridge(ArchitectModelRouter(repo_root=tmp_path))

    eligibility = bridge._builder_patch_grounding_eligibility(
        build_builder_context_packet(
            target_file="demo.py",
            target_symbol="answer",
            grounding_evidence={"codemap_symbol_hits": [{"file": "demo.py", "name": "answer", "line": 1, "end_line": 2}]},
            codemap=json.loads((tmp_path / ".aura" / "CODEMAP.json").read_text(encoding="utf-8")),
            repo_root=tmp_path,
            topological_grounding=grounding,
        )
    )

    assert eligibility["ok"] is True
    assert eligibility["route"] == "BUILDER_PATCH"


def test_act_tasks_topological_grounding_overrides_stale_task_data(tmp_path: Path):
    _write_demo_repo(tmp_path, with_tests=True)
    from aura_live_architect import _attach_grounding_to_plan

    grounding = ground_coding_arena_intent("patch answer", tmp_path, target_symbol="answer")
    plan = {
        "target_file": "demo.py",
        "target_symbol": "answer",
        "act_tasks": [
            {
                "task_id": "A1",
                "objective": "patch answer",
                "target_file": "old_demo.py",
                "target_symbol": "old_answer",
                "topological_grounding": {
                    "route": "LOCALIZE_FIRST",
                    "safety_policy": "stale_policy",
                },
            }
        ],
    }

    updated = _attach_grounding_to_plan(plan, grounding)

    assert updated["act_tasks"][0]["topological_grounding"]["route"] == "BUILDER_PATCH"
    assert updated["act_tasks"][0]["topological_grounding"]["safety_policy"] == "exact_source_spans_and_hashes_only"
