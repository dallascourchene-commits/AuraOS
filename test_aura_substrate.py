"""
Offline self-check for the Aura substrate (aura_substrate.py).

These tests exercise ONLY the deterministic, LLM-free core: intent compression,
surgical context selection, guardrail loading, token accounting, and the
benchmark's unified-diff applier / quality scorer. No network, no model.

Run:  python3 test_aura_substrate.py
"""

from __future__ import annotations

import sys

import json

from aura_substrate import (
    PACKET_STYLES,
    AuraSubstrate,
    ContextSelector,
    IntentCompressor,
    estimate_tokens,
    extract_function_source,
    load_guardrails,
    parse_master_key_header,
    render_packet,
)

_PASS = 0
_FAIL = 0


def _run(name: str, fn) -> None:
    global _PASS, _FAIL
    try:
        fn()
        print(f"  [PASS] {name}")
        _PASS += 1
    except AssertionError as e:
        print(f"  [FAIL] {name}: {e}")
        _FAIL += 1
    except Exception as e:  # noqa: BLE001
        print(f"  [ERR ] {name}: {type(e).__name__}: {e}")
        _FAIL += 1


def test_token_estimator() -> None:
    assert estimate_tokens("") == 0
    assert estimate_tokens("abcd") == 1
    assert estimate_tokens("a" * 400) == 100


def test_header_index() -> None:
    content = ContextSelector().read("aura_mesh.py")
    hdr = parse_master_key_header(content)
    assert "FUNCTIONS" in hdr, "expected FUNCTIONS in mesh header"
    assert "offload_compute" in hdr["FUNCTIONS"]


def test_function_extraction() -> None:
    content = ContextSelector().read("aura_mesh.py")
    src, start, end = extract_function_source(content, "offload_compute")
    assert src is not None and end > start
    assert "async def offload_compute" in src


def test_intent_compressor() -> None:
    c = IntentCompressor()
    packet = c.compress(
        "fix the mesh offload without adding new deps, preserve the protocol, give a diff",
        explicit_tags=["TARGET:OFFLOAD_COMPUTE"],
    )
    for tag in ("[TARGET:OFFLOAD_COMPUTE]", "[OP:PATCH]", "[CONSTRAINT:NO_NEW_DEPS]",
                "[DOMAIN:MESH]", "[OUTPUT:UNIFIED_DIFF]"):
        assert tag in packet, f"missing {tag} in {packet}"


def test_guardrails_present() -> None:
    g = load_guardrails()
    for marker in ("AURA", "SECURITY", "OUTPUT FORMATS", "No new dependencies"):
        assert marker in g, f"guardrail missing marker: {marker}"


def test_substrate_is_llm_free_and_surgical() -> None:
    pkg = AuraSubstrate().compile(
        "fix the mesh offload without adding new deps, preserve the protocol",
        target_file="aura_mesh.py",
        target_func="offload_compute",
        explicit_tags=["ENV:PYTHON", "OP:PATCH", "OUTPUT:UNIFIED_DIFF"],
    )
    assert pkg.meta["llm_used"] is False
    full_lines = len(ContextSelector().read("aura_mesh.py").splitlines())
    assert pkg.context.exposed_lines < full_lines, "surgical context should be smaller than full file"
    assert estimate_tokens(pkg.prompt) > 0


def test_packet_styles() -> None:
    tags = ["ENV:PYTHON", "OP:PATCH", "DOMAIN:MESH", "TARGET:OFFLOAD_COMPUTE",
            "CONSTRAINT:NO_NEW_DEPS", "CONSTRAINT:PRESERVE_PROTOCOL",
            "VERIFY:AST_PARSE", "OUTPUT:UNIFIED_DIFF"]
    # all styles render
    for style in PACKET_STYLES:
        out = render_packet(tags, style)
        assert out.strip(), f"empty render for {style}"

    assert render_packet(tags, "bracket").startswith("[ENV:PYTHON]")

    obj = json.loads(render_packet(tags, "json"))
    assert obj["OP"] == "PATCH"
    assert obj["CONSTRAINT"] == ["NO_NEW_DEPS", "PRESERVE_PROTOCOL"], "repeats -> list"

    yml = render_packet(tags, "yaml")
    assert "OP: PATCH" in yml and "  - NO_NEW_DEPS" in yml

    hyb = render_packet(tags, "hybrid")
    assert "[OP:PATCH]" in hyb and "NO_NEW_DEPS" in hyb

    try:
        render_packet(tags, "bogus")
        assert False, "expected ValueError for bad style"
    except ValueError:
        pass


def test_mock_matrix_offline() -> None:
    from aura_matrix_benchmark import run_matrix
    modes = ["unified_diff", "json_edit_plan"]
    res = run_matrix("mesh_offload", ["mock"], list(PACKET_STYLES), mock=True,
                     output_modes=modes)
    assert len(res["rows"]) == len(PACKET_STYLES) * len(modes)
    for r in res["rows"]:
        assert r["aura_quality"] >= r["raw_quality"], "aura should not be worse in mock"
        assert r["output_mode"] in modes
        assert "aura_total_cost_usd" in r and "aura_output_tokens" in r
    lb = res["leaderboard"]
    for key in ("best_quality", "best_total_cost", "best_latency", "best_overall"):
        assert key in lb and lb[key]["provider"] == "mock"
    assert "mock" in lb["preferred_style_per_provider"]


def test_json_edit_plan_scoring() -> None:
    from aura_proxy_benchmark import (
        parse_edit_plan, apply_edit_plan, edit_plan_to_unified_diff,
        QualityScorer, TASKS, with_output_mode,
    )
    original = ContextSelector().read("aura_mesh.py")
    good = ('{"edits": [{"file": "aura_mesh.py", "start_line": 174, "end_line": 174, '
            '"replacement": "            secure_packet = '
            'self.pack_secure_polysynthetic_packet([0, 0, 0, 0, 0, 0], 1.0)"}]}')
    plan, note = parse_edit_plan(good)
    assert plan is not None and note == "ok"
    patched, n = apply_edit_plan(original, plan)
    assert patched is not None and "[0, 0, 0, 0, 0, 0], 1.0" in patched
    diff = edit_plan_to_unified_diff(original, plan, "aura_mesh.py")
    assert diff.startswith("--- a/aura_mesh.py") and "@@" in diff

    task = with_output_mode(TASKS["mesh_offload"], "json_edit_plan")
    scorer = QualityScorer({"aura_mesh.py"}, {"socket"}, original, target_func="offload_compute")
    res = scorer.score(good, task)
    assert res["score"] == 1.0, f"clean edit plan should score 1.0: {res}"
    # a fabricated-file edit plan must be rejected
    bad = ('{"edits": [{"file": "ghost.py", "start_line": 1, "end_line": 1, '
           '"replacement": "x = 1"}]}')
    rbad = scorer.score(bad, task)
    assert rbad["checks"]["no_fake_files"] is False


def test_provider_classification() -> None:
    from aura_llm_egress import classify_providers, usable_providers, PROVIDERS
    # placeholder + non-placeholder keys
    secrets = {"MISTRAL_API_KEY": "real-key", "OPENAI_API_KEY": "your_key_here"}
    buckets = classify_providers(secrets)
    assert "mistral" in buckets["working"]
    assert "openai" in buckets["placeholder"], "placeholder key must not count as configured"
    assert "anthropic" in PROVIDERS  # placeholder present in catalog for future keys
    assert usable_providers(secrets) == ["mistral"]


def test_router_ledger_selection() -> None:
    import tempfile, os as _os
    from aura_router import CalibrationLedger, DEFAULT_STYLE, DEFAULT_MODE
    tmp = tempfile.mkdtemp()
    led = CalibrationLedger(_os.path.join(tmp, "cal.jsonl"))
    # two providers calibrated for task_type 'patch'
    led.append({"ts": "2026-01-01T00:00:00Z", "task_type": "patch", "provider": "mistral",
                "style": "bracket", "output_mode": "json_edit_plan", "overall_score": 0.95,
                "aura_quality": 1.0})
    led.append({"ts": "2026-01-01T00:00:00Z", "task_type": "patch", "provider": "sambanova",
                "style": "hybrid", "output_mode": "unified_diff", "overall_score": 0.80,
                "aura_quality": 1.0})
    # auto: highest overall first
    cands = led.best_candidates("patch", ["mistral", "sambanova"])
    assert cands[0]["provider"] == "mistral" and cands[0]["style"] == "bracket"
    # forced model reorders priority to put it first
    forced = led.best_candidates("patch", ["mistral", "sambanova"], prefer_model="sambanova")
    assert forced[0]["provider"] == "sambanova"
    # newest record supersedes older for the same key
    led.append({"ts": "2026-02-01T00:00:00Z", "task_type": "patch", "provider": "mistral",
                "style": "bracket", "output_mode": "json_edit_plan", "overall_score": 0.10,
                "aura_quality": 0.5})
    cands2 = led.best_candidates("patch", ["mistral", "sambanova"])
    assert cands2[0]["provider"] == "sambanova", "stale low score should drop mistral"
    # cold start: unknown provider with no data -> default style/mode
    cold = led.best_candidates("patch", ["groq"])
    assert cold[0]["style"] == DEFAULT_STYLE and cold[0]["output_mode"] == DEFAULT_MODE


def test_router_mock_route_and_savings() -> None:
    import tempfile, os as _os
    from aura_router import CalibrationLedger, ExecutionLog, calibrate, AutoRouter, savings_report
    from aura_matrix_benchmark import MockEgress
    tmp = tempfile.mkdtemp()
    led = CalibrationLedger(_os.path.join(tmp, "cal.jsonl"))
    elog = ExecutionLog(_os.path.join(tmp, "exec.jsonl"))
    # mock calibration populates the ledger
    calibrate("mesh_offload", ["mock"], ["bracket"], ["unified_diff", "json_edit_plan"],
              trials=1, mock=True, ledger=led)
    assert len(led.latest()) >= 2
    # route using the ledger + a mock egress
    router = AutoRouter(ledger=led, exec_log=elog, egress_factory=lambda p: MockEgress(provider=p))
    res = router.route("mesh_offload", mock=True)
    assert res["ok"] is True
    assert res["record"]["chosen_provider"] == "mock"
    assert "--- a/aura_mesh.py" in res["artifact"], "edit plan/diff should expand to a diff"
    rep = savings_report(ledger=led, exec_log=elog)
    assert rep["executions"] == 1
    assert "patch" in rep["projection_if_optimal"]


def test_sanitize_code() -> None:
    from aura_substrate import sanitize_code
    dirty = 'x = 1  # em\u2014dash and \u201csmart\u201d \u2018quotes\u2019\u2026'
    clean, repl = sanitize_code(dirty)
    assert "\u2014" not in clean and "\u201c" not in clean and "\u2018" not in clean
    assert "..." in clean and repl, "should report replacements"
    import ast as _ast
    _ast.parse(clean)  # now parses


def test_pricing_book() -> None:
    import tempfile, os as _os, time as _time
    from aura_pricing import PriceBook
    pb = PriceBook(_os.path.join(tempfile.mkdtemp(), "pricing.json"))
    pin, pout = pb.price("mistral")
    assert pin > 0 and pout > 0
    assert pb.cost("mistral", 1000, 1000) == round(pin + pout, 6)
    assert pb.is_stale(days=7) is False  # just created
    pb.update("mistral", 0.001, 0.002)
    assert pb.price("mistral") == (0.001, 0.002)
    changed = pb.maybe_refresh(fetcher=lambda: {"mistral": {"in_per_1k": 0.005, "out_per_1k": 0.006}},
                               days=-1)  # force stale
    assert changed and pb.price("mistral") == (0.005, 0.006)


def test_converse_mock_and_learning() -> None:
    import tempfile, os as _os
    from aura_converse import Conversationalist, CommProfile, ConversationLog, parse_feedback
    from aura_router import ExecutionLog
    from aura_matrix_benchmark import MockEgress
    tmp = tempfile.mkdtemp()
    prof = CommProfile(_os.path.join(tmp, "profile.json"))
    convo = ConversationLog(_os.path.join(tmp, "convo.jsonl"))
    elog = ExecutionLog(_os.path.join(tmp, "exec.jsonl"))
    c = Conversationalist(egress_factory=lambda p: MockEgress(provider=p),
                          profile=prof, convo_log=convo, exec_log=elog)
    res = c.converse("explain the mesh offload", mock=True)
    assert res["ok"] and "Mock reply" in res["rendered"]
    turns = convo.read_all()
    assert turns and turns[-1]["packet"].startswith("[") and turns[-1]["ts"]
    assert elog.read_all()[-1]["aspect"] == "conversation"
    # learning: natural correction adjusts the profile + dips DKT mastery
    assert parse_feedback("can you say it shorter")["verbosity"] == "terse"
    before = prof.data["dkt_mastery"]
    c.give_feedback("I don't understand, say it more like: keep it simple")
    assert prof.data["verbosity"] == "terse"
    assert prof.data["style_refs"], "liked exemplar should be learned"
    assert prof.data["dkt_mastery"] <= before


def test_savings_by_provider_and_aspect() -> None:
    import tempfile, os as _os
    from aura_router import ExecutionLog, CalibrationLedger, savings_report
    tmp = tempfile.mkdtemp()
    elog = ExecutionLog(_os.path.join(tmp, "exec.jsonl"))
    elog.append({"chosen_provider": "mistral", "aspect": "refactor", "aura_input_tokens": 500,
                 "aura_output_tokens": 50, "aura_total_cost_usd": 0.0001,
                 "raw_input_tokens": 2500, "est_raw_output_tokens": 600,
                 "est_raw_total_cost_usd": 0.001})
    elog.append({"chosen_provider": "sambanova", "aspect": "conversation", "aura_input_tokens": 300,
                 "aura_output_tokens": 40, "aura_total_cost_usd": 0.0003,
                 "raw_input_tokens": 1500, "est_raw_output_tokens": 400,
                 "est_raw_total_cost_usd": 0.002})
    led = CalibrationLedger(_os.path.join(tmp, "cal.jsonl"))
    rep = savings_report(ledger=led, exec_log=elog)
    assert rep["executions"] == 2
    assert "mistral" in rep["by_provider"] and "sambanova" in rep["by_provider"]
    assert "refactor" in rep["by_aspect"] and "conversation" in rep["by_aspect"]
    assert rep["overall"]["input_tokens_saved"] == (2500 - 500) + (1500 - 300)


def test_sandbox_task_and_no_fake_files() -> None:
    from aura_proxy_benchmark import TASKS, with_output_mode, QualityScorer, _repo_py_files
    from aura_substrate import ContextSelector, existing_import_roots
    assert "sandbox_score" in TASKS
    assert "sample_target.py" in _repo_py_files(), "sandbox files must be allowed refs"
    task = with_output_mode(TASKS["sandbox_score"], "json_edit_plan")
    original = ContextSelector().read(task.target_file)
    scorer = QualityScorer(_repo_py_files(), existing_import_roots(original),
                           original, target_func="compute_score")
    good = ('{"edits": [{"file": "Aura_Sandbox/sample_target.py", "start_line": 21, '
            '"end_line": 21, "replacement": "    return 0.0 if not values else '
            'weight * sum(values) / len(values)"}]}')
    res = scorer.score(good, task)
    assert res["checks"]["no_fake_files"] is True


def test_diff_applier_and_scorer() -> None:
    from aura_proxy_benchmark import _apply_unified_diff, QualityScorer, TASKS
    sel = ContextSelector()
    original = sel.read("aura_mesh.py")
    diff = (
        "--- a/aura_mesh.py\n+++ b/aura_mesh.py\n"
        "@@ -165,1 +165,1 @@\n"
        "-        start_time = time.time()\n"
        "+        start_time = time.time()  # patched\n"
    )
    patched, note = _apply_unified_diff(original, diff)
    assert patched is not None, f"diff failed to apply: {note}"
    assert "# patched" in patched

    scorer = QualityScorer({"aura_mesh.py"}, {"socket"}, original, target_func="offload_compute")
    # a fabricated-file + new-dependency answer should score poorly
    bad = "```python\nimport requests\nfrom fake_helper import x  # see fake_helper.py\n```"
    res = scorer.score(bad, TASKS["mesh_offload"])
    assert res["checks"]["no_fake_files"] is False, f"expected fake file flagged: {res['notes']}"
    assert res["checks"]["no_forbidden_deps"] is False, f"expected forbidden dep flagged: {res['notes']}"


def main() -> int:
    print("== Aura substrate self-check (offline, no LLM) ==")
    _run("token estimator", test_token_estimator)
    _run("master-key header index", test_header_index)
    _run("function extraction", test_function_extraction)
    _run("intent compressor", test_intent_compressor)
    _run("guardrails present", test_guardrails_present)
    _run("substrate is LLM-free + surgical", test_substrate_is_llm_free_and_surgical)
    _run("packet styles (bracket/json/yaml/hybrid)", test_packet_styles)
    _run("mock matrix offline + leaderboard", test_mock_matrix_offline)
    _run("json edit plan parse/apply/score", test_json_edit_plan_scoring)
    _run("provider classification + placeholders", test_provider_classification)
    _run("router ledger selection + override + cold start", test_router_ledger_selection)
    _run("router mock route + savings", test_router_mock_route_and_savings)
    _run("ascii sanitizer", test_sanitize_code)
    _run("pricing book + weekly refresh", test_pricing_book)
    _run("converse mock + learning/DKT", test_converse_mock_and_learning)
    _run("savings by provider + aspect", test_savings_by_provider_and_aspect)
    _run("sandbox task + no fake files", test_sandbox_task_and_no_fake_files)
    _run("diff applier + quality scorer", test_diff_applier_and_scorer)
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
