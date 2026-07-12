"""Contracts for the guided no-LLM bulk-intent routing demonstration."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parent.parent
SLOT_KEYS = {"DIR", "ASP", "CLASS", "SUBJ", "VOICE", "STEM"}


def _topology() -> dict:
    nodes = [
        {
            "id": "file:intent-ingestion",
            "label": "aura_intent_ingestion.py",
            "node_type": "file",
            "file_path": "aura_intent_ingestion.py",
            "symbol": "global_scope",
            "line_range": [1, 1068],
            "tokens_est": 5200,
            "color": "#4f8cff",
            "x": -85,
            "y": 10,
            "z": 20,
            "metadata": {},
        },
        {
            "id": "symbol:compile-intent",
            "label": "compile_intent_packet",
            "node_type": "function",
            "file_path": "aura_intent_ingestion.py",
            "symbol": "compile_intent_packet",
            "line_range": [477, 735],
            "tokens_est": 1800,
            "color": "#38c98b",
            "x": 25,
            "y": -20,
            "z": 35,
            "metadata": {},
        },
        {
            "id": "file:fst-routing",
            "label": "aura_fst_routing.py",
            "node_type": "router",
            "file_path": "aura_fst_routing.py",
            "symbol": "global_scope",
            "line_range": [1, 1020],
            "tokens_est": 4800,
            "color": "#c084fc",
            "x": 90,
            "y": 20,
            "z": -15,
            "metadata": {},
        },
        {
            "id": "test:intent-ingestion",
            "label": "test_aura_intent_ingestion.py",
            "node_type": "test",
            "file_path": "tests/test_aura_intent_ingestion.py",
            "symbol": "global_scope",
            "line_range": [1, 237],
            "tokens_est": 1100,
            "color": "#ef5da8",
            "x": 40,
            "y": 85,
            "z": 10,
            "metadata": {},
        },
    ]
    links = [
        {"source": "file:intent-ingestion", "target": "symbol:compile-intent", "type": "contains", "status": "known"},
        {"source": "symbol:compile-intent", "target": "file:fst-routing", "type": "routes_to", "status": "known"},
        {"source": "test:intent-ingestion", "target": "symbol:compile-intent", "type": "tested_by", "status": "known"},
    ]
    return {"nodes": nodes, "links": links, "meta": {"truth_policy": "exact"}}


def test_bulk_intent_compiles_without_a_model_and_exposes_real_routing_layers():
    from aura_showcase_intent import DEFAULT_BULK_INTENT, compile_bulk_intent_trace

    result = compile_bulk_intent_trace(
        DEFAULT_BULK_INTENT,
        repo_root=REPO_ROOT,
        include_grounding=False,
    )

    assert result["ok"] is True
    assert result["model_calls_made"] == 0
    assert result["parse_mode"] == "deterministic_local_pre_llm"
    assert result["lexical_codebook"]["primitive_count"] == 4096
    assert result["lexical_codebook"]["address_width_bits"] == 12
    assert result["lexical_codebook"]["tokens"]
    assert set(result["six_slot_packet"]["slots"]) == SLOT_KEYS
    assert result["six_slot_packet"]["vsa_binding"]
    assert result["machine_route"]["rule_name"]
    assert result["machine_route"]["route"]
    assert result["lexc_trace"]["available"] is True
    assert result["lexc_trace"]["arc_count"] > 0
    assert result["lexc_trace"]["complete_route_count_bounded"] > 0

    input_prefixes = {item["symbol"].split(":", 1)[0] for item in result["machine_symbol_trace"]["input"]}
    output_prefixes = {item["symbol"].split(":", 1)[0] for item in result["machine_symbol_trace"]["output"]}
    assert input_prefixes == {"I", "A", "X", "S", "R", "G", "T", "Q", "C"}
    assert output_prefixes == {"O", "M", "K", "E", "V"}
    assert result["agent_handoff"]["compressed_context"]
    assert result["automatic_commit"] is False
    assert result["automatic_push"] is False
    assert result["automatic_merge"] is False


def test_bulk_intent_redacts_secret_like_text_before_display_or_handoff():
    from aura_showcase_intent import compile_bulk_intent_trace

    secret = "sk-project-this-must-never-appear-123456789"
    result = compile_bulk_intent_trace(
        f"Refactor the routing demo and use api_key={secret} while preserving tests.",
        repo_root=REPO_ROOT,
        include_grounding=False,
    )

    assert result["ok"] is True
    assert result["redactions_applied"] >= 1
    assert secret not in result["raw_intent"]
    assert secret not in result["objective"]
    assert secret not in result["agent_handoff"]["compressed_context"]
    assert "[REDACTED_SECRET]" in result["raw_intent"]


def test_bulk_intent_size_and_empty_input_fail_closed():
    from aura_showcase_intent import MAX_BULK_INTENT_CHARS, compile_bulk_intent_trace

    empty = compile_bulk_intent_trace("", repo_root=REPO_ROOT, include_grounding=False)
    assert empty["ok"] is False
    assert empty["error"] == "bulk_intent_required"
    assert empty["model_calls_made"] == 0

    oversized = compile_bulk_intent_trace(
        "x" * (MAX_BULK_INTENT_CHARS + 1),
        repo_root=REPO_ROOT,
        include_grounding=False,
    )
    assert oversized["ok"] is False
    assert oversized["error"] == "bulk_intent_too_large"
    assert oversized["max_chars"] == MAX_BULK_INTENT_CHARS


def test_compiled_intent_reuses_existing_bounded_topology_adapter():
    from aura_showcase_intent_topology import build_intent_workspace

    trace = {
        "ok": True,
        "objective": "Improve compile_intent_packet and preserve routing tests.",
        "likely_files": ["aura_intent_ingestion.py", "aura_fst_routing.py"],
        "likely_symbols": ["compile_intent_packet"],
        "keywords": ["intent", "routing", "compile"],
        "six_slot_packet": {
            "slots": {
                "DIR": "PLAN_ONLY",
                "ASP": "BOUNDED",
                "CLASS": "CODE_REFACTOR",
                "SUBJ": "PYTHON_MODULE:SYMBOL",
                "VOICE": "NO_MODEL",
                "STEM": "MODIFY",
            }
        },
    }

    result = build_intent_workspace(_topology(), trace, depth=2)
    assert result["ok"] is True
    assert result["task"]["task_id"] == "compiled_bulk_intent"
    assert set(result["task"]["intent_slots"]) == SLOT_KEYS
    assert result["workspace"]["selected_node_ids"]
    assert result["workspace"]["returned_node_count"] <= result["bounds"]["node_limit"]
    assert result["workspace"]["returned_link_count"] <= result["bounds"]["link_limit"]
    assert all(node["patch_authority"] is False for node in result["workspace"]["nodes"])
    assert result["automatic_commit"] is False
    assert result["automatic_push"] is False
    assert result["automatic_merge"] is False


def test_showcase_dispatch_compiles_bulk_intent_and_attaches_bounded_topology():
    from aura_showcase_server import dispatch_showcase_request

    state = SimpleNamespace(
        repo_root=REPO_ROOT,
        default_session_id="",
        demo_project="winnipeg_pathways",
        human_agent=SimpleNamespace(arena=SimpleNamespace(topology=_topology())),
    )
    status, _, raw = dispatch_showcase_request(
        state,
        "POST",
        "/api/showcase/intent/compile",
        {
            "text": "Improve compile_intent_packet routing and preserve its tests.",
            "include_grounding": False,
            "include_topology": True,
            "depth": 1,
        },
    )
    result = json.loads(raw)
    assert status == 200
    assert result["ok"] is True
    assert result["model_calls_made"] == 0
    assert set(result["six_slot_packet"]["slots"]) == SLOT_KEYS
    assert result["topology_packet"]["ok"] is True
    assert result["topology_packet"]["workspace"]["returned_node_count"] <= 96
    assert result["patch_authority"] == "exact_source_spans_and_hashes_only"
    assert result["automatic_merge"] is False


def test_browser_assets_present_usable_learning_workspace_with_optional_tour():
    index = (REPO_ROOT / "aura_showcase" / "index.html").read_text(encoding="utf-8")
    app_js = (REPO_ROOT / "aura_showcase" / "app.js").read_text(encoding="utf-8")
    intent_js = (REPO_ROOT / "aura_showcase" / "intent.js").read_text(encoding="utf-8")
    intent_css = (REPO_ROOT / "aura_showcase" / "intent.css").read_text(encoding="utf-8")
    server = (REPO_ROOT / "aura_showcase_server.py").read_text(encoding="utf-8")

    assert 'data-tab="learning"' in index
    assert 'id="learning-view"' in index
    assert 'id="bulk-intent-input"' in index
    assert 'id="learning-rail"' in index
    assert 'id="compiled-six-slots"' in index
    assert 'id="machine-input-symbols"' in index
    assert 'id="machine-output-symbols"' in index
    assert 'id="learning-topology-canvas"' in index
    assert 'href="intent.css"' in index
    assert 'src="intent.js"' in index

    assert "/api/showcase/intent/compile" in intent_js
    assert "model calls: 0" in intent_js
    assert "include_topology: true" in intent_js

    assert "Use Aura freely—or follow the suggested tour." in app_js
    assert "S.startLearningTour" in app_js
    assert "S.exitLearningTour" in app_js
    assert "S.toggleLearningOverview" in app_js
    assert "Compiled workspace ready · every view is now available" in app_js
    assert "Copy worker handoff" in app_js
    assert "Copy trace JSON" in app_js
    assert "Export JSON" in app_js
    assert "LEARNING_EXAMPLES" in app_js
    assert "document.querySelectorAll('[data-learning-stage]')" in app_js
    assert "button.disabled = false" in app_js

    assert "#learning-view.is-overview .learning-panel" in intent_css
    assert ".learning-workspace-toolbar" in intent_css
    assert ".learning-tour-note" in intent_css
    assert ".learning-examples" in intent_css

    assert '"intent.js"' in server
    assert '"intent.css"' in server
    assert "model_calls_before_handoff" in server
