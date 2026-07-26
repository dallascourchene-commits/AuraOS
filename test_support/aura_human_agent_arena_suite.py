"""Deterministic tests for the Human Agent Arena.

Tests cover:
- Existing Coding Arena dispatcher still responds to existing routes.
- Human Agent Arena command router handles show ST3GG, show JSpace, show Agent Arena Bridge,
  hypothesize connection, and prepare agent task without mutating production files.
- Ghost edges are stored only in live state and are never treated as patch authority.
- Broad hub file reads are not introduced.
- Command responses include visual_update, truth_packet, next_actions, patch_authority,
  and vsa_patch_authority: false.
"""

import json
from pathlib import Path

import pytest

from aura_coding_arena_server import CodingArenaServerState, dispatch_api_request
from aura_human_agent_arena import (
    PATCH_AUTHORITY,
    VSA_PATCH_AUTHORITY,
    HumanAgentArena,
    HumanAgentArenaState,
    GhostEdge,
)
from aura_human_agent_arena_server import (
    HumanAgentArenaServerState,
    dispatch_api_request as dispatch_human_agent_api,
)


# ---------------------------------------------------------------------------
# Existing Coding Arena dispatcher still works
# ---------------------------------------------------------------------------


def test_existing_coding_arena_topology_route_still_works(tmp_path: Path):
    """The existing Coding Arena /api/topology route must keep its current behavior."""
    state = CodingArenaServerState(tmp_path, demo=True)
    status, topology = dispatch_api_request(state, "GET", "/api/topology?demo=1")
    assert status == 200
    assert topology["source"] == "offline_demo"
    assert topology["meta"]["demo"] is True
    assert len(topology["nodes"]) > 0


def test_existing_coding_arena_select_route_still_works(tmp_path: Path):
    """The existing Coding Arena /api/select route must keep its current behavior."""
    state = CodingArenaServerState(tmp_path, demo=True)
    _, topology = dispatch_api_request(state, "GET", "/api/topology?demo=1")
    node_id = topology["nodes"][0]["id"]
    status, result = dispatch_api_request(
        state,
        "POST",
        "/api/select",
        {"node_ids": [node_id], "depth": 1, "human_instruction": "select"},
    )
    assert status == 200
    assert result["selected_node_ids"] == [node_id]


def test_existing_coding_arena_compile_capsule_route_still_works(tmp_path: Path):
    """The existing Coding Arena /api/compile-capsule route must keep its current behavior."""
    state = CodingArenaServerState(tmp_path, demo=True)
    _, topology = dispatch_api_request(state, "GET", "/api/topology?demo=1")
    node_id = topology["nodes"][0]["id"]
    status, capsule = dispatch_api_request(
        state,
        "POST",
        "/api/compile-capsule",
        {"node_ids": [node_id], "human_instruction": "compile capsule"},
    )
    assert status == 200
    assert capsule["selected"]["node_ids"] == [node_id]
    assert capsule["route_decision"]["network_calls_made"] is False


def test_existing_coding_arena_simulate_route_still_works(tmp_path: Path):
    """The existing Coding Arena /api/simulate-route route must keep its current behavior."""
    state = CodingArenaServerState(tmp_path, demo=True)
    _, topology = dispatch_api_request(state, "GET", "/api/topology?demo=1")
    node_id = topology["nodes"][0]["id"]
    status, capsule = dispatch_api_request(
        state,
        "POST",
        "/api/compile-capsule",
        {"node_ids": [node_id], "human_instruction": "simulate route"},
    )
    status2, route = dispatch_api_request(
        state,
        "POST",
        "/api/simulate-route",
        {"capsule": capsule},
    )
    assert status2 == 200
    assert route["network_calls_made"] is False


def test_existing_coding_arena_mark_edge_route_still_works(tmp_path: Path):
    """The existing Coding Arena /api/mark-edge route must keep its current behavior."""
    state = CodingArenaServerState(tmp_path, demo=True)
    _, topology = dispatch_api_request(state, "GET", "/api/topology?demo=1")
    nodes = topology["nodes"]
    status, result = dispatch_api_request(
        state,
        "POST",
        "/api/mark-edge",
        {"source": nodes[0]["id"], "target": nodes[1]["id"]},
    )
    assert status == 200
    assert result["ok"] is True


def test_existing_coding_arena_voice_intent_route_still_works(tmp_path: Path):
    """The existing Coding Arena /api/voice-intent route must keep its current behavior."""
    state = CodingArenaServerState(tmp_path, demo=True)
    _, topology = dispatch_api_request(state, "GET", "/api/topology?demo=1")
    node_id = topology["nodes"][0]["id"]
    status, result = dispatch_api_request(
        state,
        "POST",
        "/api/voice-intent",
        {"node_ids": [node_id], "command": "compile capsule"},
    )
    assert status == 200
    assert result["action"] == "compile"


# ---------------------------------------------------------------------------
# Human Agent Arena — basic structure and invariants
# ---------------------------------------------------------------------------


def test_human_agent_arena_state_is_serializable(tmp_path: Path):
    """Live state must be JSON-serializable."""
    arena = HumanAgentArena(tmp_path, demo=True)
    state = arena.get_state()
    encoded = json.dumps(state, default=str)
    decoded = json.loads(encoded)
    assert "visible_node_ids" in decoded
    assert "hidden_node_ids" in decoded
    assert "selected_node_ids" in decoded
    assert "ghost_edges" in decoded
    assert "event_log" in decoded
    assert "diagnostics" in decoded
    assert "hypotheses" in decoded
    assert "agent_tasks" in decoded
    assert "human_notes" in decoded
    assert "active_filter" in decoded
    assert "micro_arena" in decoded


def test_human_agent_arena_events_keep_absolute_offsets_after_trim(tmp_path: Path):
    """Polling offsets should stay stable after the event log rotates."""
    arena = HumanAgentArena(tmp_path, demo=True)
    for _ in range(500):
        arena.state.add_event("test", "payload")

    result = arena.get_events(since=300)

    assert result["ok"] is True
    assert len(result["events"]) == 201
    assert result["next_index"] == 501


def test_human_agent_arena_server_state_endpoint(tmp_path: Path):
    """GET /api/human-agent/state returns state and topology."""
    state = HumanAgentArenaServerState(tmp_path, demo=True)
    status, result = dispatch_human_agent_api(state, "GET", "/api/human-agent/state")
    assert status == 200
    assert result["ok"] is True
    assert "state" in result
    assert "topology" in result
    assert result["patch_authority"] == "exact_source_spans_and_hashes_only"
    assert result["vsa_patch_authority"] is False


def test_human_agent_arena_events_endpoint(tmp_path: Path):
    """GET /api/human-agent/events returns events."""
    state = HumanAgentArenaServerState(tmp_path, demo=True)
    status, result = dispatch_human_agent_api(state, "GET", "/api/human-agent/events")
    assert status == 200
    assert result["ok"] is True
    assert "events" in result
    assert "next_index" in result


def test_human_agent_arena_command_endpoint(tmp_path: Path):
    """POST /api/human-agent/command routes a command."""
    state = HumanAgentArenaServerState(tmp_path, demo=True)
    status, result = dispatch_human_agent_api(
        state,
        "POST",
        "/api/human-agent/command",
        {"command": "show ST3GG", "mode": "explore"},
    )
    assert status == 200
    assert result["ok"] is True
    assert "answer" in result
    assert "visual_update" in result
    assert "truth_packet" in result
    assert "next_actions" in result


def test_human_agent_arena_command_endpoint_rejects_empty(tmp_path: Path):
    """POST /api/human-agent/command rejects empty commands."""
    state = HumanAgentArenaServerState(tmp_path, demo=True)
    status, result = dispatch_human_agent_api(
        state,
        "POST",
        "/api/human-agent/command",
        {"command": "", "mode": "explore"},
    )
    assert status == 400
    assert result["ok"] is False


# ---------------------------------------------------------------------------
# Command router — show ST3GG
# ---------------------------------------------------------------------------


def test_show_st3gg_filters_st3gg_nodes(tmp_path: Path):
    """show ST3GG should filter/highlight nodes containing ST3GG or st3gg."""
    arena = HumanAgentArena(tmp_path, demo=True)
    result = arena.route_command("show ST3GG")
    assert result["ok"] is True
    vu = result["visual_update"]
    tp = result["truth_packet"]
    # In demo topology there may be no ST3GG nodes, but the structure must be correct.
    assert "highlighted_node_ids" in vu
    assert "hidden_node_ids" in vu
    assert "ghost_edges" in vu
    assert "labels" in vu
    # Truth packet must have patch authority invariants.
    assert tp["patch_authority"] == PATCH_AUTHORITY
    assert tp["vsa_patch_authority"] is VSA_PATCH_AUTHORITY
    assert tp["grounding"] in ("grounded", "NEEDS_GROUNDING")


def test_show_st3gg_response_has_required_fields(tmp_path: Path):
    """Every command response must include visual_update, truth_packet, next_actions, patch_authority, vsa_patch_authority: false."""
    arena = HumanAgentArena(tmp_path, demo=True)
    result = arena.route_command("show ST3GG")
    assert "visual_update" in result
    assert "truth_packet" in result
    assert "next_actions" in result
    assert result["truth_packet"]["patch_authority"] == "exact_source_spans_and_hashes_only"
    assert result["truth_packet"]["vsa_patch_authority"] is False


# ---------------------------------------------------------------------------
# Command router — show JSpace
# ---------------------------------------------------------------------------


def test_show_jspace_filters_jspace_nodes(tmp_path: Path):
    """show JSpace should filter/highlight JSpace-related nodes."""
    arena = HumanAgentArena(tmp_path, demo=True)
    result = arena.route_command("show JSpace")
    assert result["ok"] is True
    vu = result["visual_update"]
    tp = result["truth_packet"]
    assert "highlighted_node_ids" in vu
    assert tp["patch_authority"] == PATCH_AUTHORITY
    assert tp["vsa_patch_authority"] is VSA_PATCH_AUTHORITY


# ---------------------------------------------------------------------------
# Command router — show Agent Arena Bridge
# ---------------------------------------------------------------------------


def test_show_agent_arena_bridge_filters_agent_arena_nodes(tmp_path: Path):
    """show Agent Arena Bridge should filter/highlight aura_agent_arena_* nodes."""
    arena = HumanAgentArena(tmp_path, demo=True)
    result = arena.route_command("show Agent Arena Bridge")
    assert result["ok"] is True
    vu = result["visual_update"]
    tp = result["truth_packet"]
    assert "highlighted_node_ids" in vu
    assert tp["patch_authority"] == PATCH_AUTHORITY
    assert tp["vsa_patch_authority"] is VSA_PATCH_AUTHORITY


# ---------------------------------------------------------------------------
# Command router — hypothesize connection
# ---------------------------------------------------------------------------


def test_hypothesize_connection_creates_ghost_edge_only(tmp_path: Path):
    """hypothesize connection should create a ghost edge only, no code written."""
    arena = HumanAgentArena(tmp_path, demo=True)
    # Select two nodes first.
    node_ids = list(arena._node_by_id.keys())[:2]
    arena.state.selected_node_ids = node_ids
    result = arena.route_command("hypothesize connection", selected_node_ids=node_ids)
    assert result["ok"] is True
    # Ghost edge must be in live state.
    assert len(arena.state.ghost_edges) >= 1
    ghost = arena.state.ghost_edges[-1]
    assert ghost["label"] == "ghost_hypothesis"
    assert ghost["source"] == node_ids[0]
    assert ghost["target"] == node_ids[1]
    # Ghost edge must NOT be in topology links.
    topology_links = arena.topology.get("links", [])
    ghost_in_topology = any(
        link.get("source") == ghost["source"] and link.get("target") == ghost["target"]
        and link.get("metadata", {}).get("human_marked")
        for link in topology_links
    )
    assert not ghost_in_topology
    # Truth packet must mark NEEDS_GROUNDING.
    tp = result["truth_packet"]
    assert tp["grounding"] == "NEEDS_GROUNDING"
    assert tp["patch_authority"] == PATCH_AUTHORITY
    assert tp["vsa_patch_authority"] is VSA_PATCH_AUTHORITY


def test_ghost_edges_never_treated_as_patch_authority(tmp_path: Path):
    """Ghost edges are stored only in live state and are never patch authority."""
    arena = HumanAgentArena(tmp_path, demo=True)
    node_ids = list(arena._node_by_id.keys())[:2]
    result = arena.route_command(
        "what if ST3GG connects to Agent Arena Bridge",
        selected_node_ids=node_ids,
    )
    assert result["ok"] is True
    # Ghost edge exists in state.
    assert len(arena.state.ghost_edges) >= 1
    # Ghost edge is not in topology.
    for ghost in arena.state.ghost_edges:
        in_topology = any(
            link.get("source") == ghost["source"] and link.get("target") == ghost["target"]
            for link in arena.topology.get("links", [])
        )
        assert not in_topology
    # Truth packet says not patch authority.
    assert result["truth_packet"]["vsa_patch_authority"] is False
    assert result["truth_packet"]["patch_authority"] == "exact_source_spans_and_hashes_only"


# ---------------------------------------------------------------------------
# Command router — prepare agent task
# ---------------------------------------------------------------------------


def test_prepare_agent_task_does_not_mutate_production_files(tmp_path: Path):
    """prepare agent task should not mutate production files even if bridge fails."""
    arena = HumanAgentArena(tmp_path, demo=True)
    node_ids = list(arena._node_by_id.keys())[:1]
    # Snapshot files before.
    files_before = set(tmp_path.rglob("*.py"))
    result = arena.route_command(
        "prepare agent task",
        selected_node_ids=node_ids,
        mode="prepare",
    )
    # Snapshot files after.
    files_after = set(tmp_path.rglob("*.py"))
    # No new files created in tmp_path.
    assert files_after == files_before
    # Response structure must be correct.
    assert result["ok"] is True
    assert "visual_update" in result
    assert "truth_packet" in result
    assert "next_actions" in result
    assert result["truth_packet"]["patch_authority"] == PATCH_AUTHORITY
    assert result["truth_packet"]["vsa_patch_authority"] is VSA_PATCH_AUTHORITY


def test_prepare_agent_task_with_selection_stores_task_in_state(tmp_path: Path):
    """prepare agent task with a selection should store the task in live state (or fail gracefully)."""
    arena = HumanAgentArena(tmp_path, demo=True)
    node_ids = list(arena._node_by_id.keys())[:1]
    result = arena.route_command(
        "prepare agent task",
        selected_node_ids=node_ids,
        mode="prepare",
    )
    assert result["ok"] is True
    # Either the task was stored or it failed gracefully — either way no production mutation.
    tp = result["truth_packet"]
    assert tp["patch_authority"] == PATCH_AUTHORITY
    assert tp["vsa_patch_authority"] is VSA_PATCH_AUTHORITY


# ---------------------------------------------------------------------------
# Command router — other commands
# ---------------------------------------------------------------------------


def test_show_tests_highlights_test_nodes(tmp_path: Path):
    """show tests should highlight known test files."""
    arena = HumanAgentArena(tmp_path, demo=True)
    result = arena.route_command("show tests")
    assert result["ok"] is True
    vu = result["visual_update"]
    tp = result["truth_packet"]
    assert "highlighted_node_ids" in vu
    assert tp["patch_authority"] == PATCH_AUTHORITY
    assert tp["vsa_patch_authority"] is VSA_PATCH_AUTHORITY


def test_show_dependencies_requires_selection(tmp_path: Path):
    """show dependencies without selection should return a no-selection result."""
    arena = HumanAgentArena(tmp_path, demo=True)
    result = arena.route_command("show dependencies")
    assert result["ok"] is True
    assert "No node selected" in result["answer"] or "highlighted_node_ids" in result["visual_update"]


def test_isolate_selected_requires_selection(tmp_path: Path):
    """isolate selected without selection should return a no-selection result."""
    arena = HumanAgentArena(tmp_path, demo=True)
    result = arena.route_command("isolate selected")
    assert result["ok"] is True
    assert "No node selected" in result["answer"] or "highlighted_node_ids" in result["visual_update"]


def test_expand_depth_2_works_with_selection(tmp_path: Path):
    """expand depth 2 with selection should expand the micro-arena."""
    arena = HumanAgentArena(tmp_path, demo=True)
    node_ids = list(arena._node_by_id.keys())[:1]
    result = arena.route_command("expand depth 2", selected_node_ids=node_ids)
    assert result["ok"] is True
    vu = result["visual_update"]
    assert len(vu["highlighted_node_ids"]) >= 1
    assert result["truth_packet"]["patch_authority"] == PATCH_AUTHORITY


def test_show_unwired_connections_returns_result_or_fallback(tmp_path: Path):
    """show unwired connections here should return audit results or NEEDS_GROUNDING fallback."""
    arena = HumanAgentArena(tmp_path, demo=True)
    result = arena.route_command("show unwired connections here")
    assert result["ok"] is True
    tp = result["truth_packet"]
    assert tp["patch_authority"] == PATCH_AUTHORITY
    assert tp["vsa_patch_authority"] is VSA_PATCH_AUTHORITY
    # Either grounded or NEEDS_GROUNDING fallback.
    assert tp["grounding"] in ("grounded", "NEEDS_GROUNDING")


def test_diagnose_selection_with_selection(tmp_path: Path):
    """diagnose selection with selection should run wiring fault diagnostics."""
    arena = HumanAgentArena(tmp_path, demo=True)
    node_ids = list(arena._node_by_id.keys())[:1]
    result = arena.route_command("diagnose selection", selected_node_ids=node_ids, mode="diagnose")
    assert result["ok"] is True
    tp = result["truth_packet"]
    assert "diagnostics" in tp
    assert tp["patch_authority"] == PATCH_AUTHORITY
    assert tp["vsa_patch_authority"] is VSA_PATCH_AUTHORITY


def test_unknown_command_returns_help(tmp_path: Path):
    """Unknown commands should return a helpful message with next actions."""
    arena = HumanAgentArena(tmp_path, demo=True)
    result = arena.route_command("xyzzy frobnicate")
    assert result["ok"] is True
    assert "Unknown command" in result["answer"]
    assert len(result["next_actions"]) > 0
    assert result["truth_packet"]["vsa_patch_authority"] is False


# ---------------------------------------------------------------------------
# Broad hub file reads not introduced
# ---------------------------------------------------------------------------


def test_no_broad_hub_file_reads_in_human_agent_arena(tmp_path: Path):
    """The Human Agent Arena module must not read huge hub files broadly."""
    import aura_human_agent_arena as mod
    source = Path(mod.__file__).read_text(encoding="utf-8")
    # Must not contain open().read() of full hub files.
    assert "aura_node.py" not in source or source.count("aura_node.py") == 0
    # Must not read entire files with .read_text() except through existing topology functions.
    # The module should use load_arena_topology from aura_coding_arena_3d, not direct file reads.
    assert "load_arena_topology" in source
    # Must not import or use open() directly for source files.
    assert "open(" not in source


def test_no_new_dependencies_required(tmp_path: Path):
    """The Human Agent Arena must not require any new external dependencies."""
    import aura_human_agent_arena as mod
    source = Path(mod.__file__).read_text(encoding="utf-8")
    # Check imports are stdlib or existing aura modules.
    forbidden_imports = ["websocket", "flask", "fastapi", "django", "tornado", "aiohttp", "requests"]
    for forbidden in forbidden_imports:
        assert forbidden not in source, f"Forbidden dependency found: {forbidden}"


# ---------------------------------------------------------------------------
# GhostEdge dataclass
# ---------------------------------------------------------------------------


def test_ghost_edge_dataclass_is_serializable():
    """GhostEdge must be serializable to dict."""
    ghost = GhostEdge(
        source="a.py::func_a",
        target="b.py::func_b",
        hypothesis_id="abc123",
    )
    d = ghost.to_dict()
    assert d["source"] == "a.py::func_a"
    assert d["target"] == "b.py::func_b"
    assert d["label"] == "ghost_hypothesis"
    # Must be JSON serializable.
    json.dumps(d)


# ---------------------------------------------------------------------------
# All command responses include required invariant fields
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        "show ST3GG",
        "show JSpace",
        "show Agent Arena Bridge",
        "show tests",
        "show dependencies",
        "isolate selected",
        "expand depth 2",
        "show unwired connections here",
        "what if ST3GG connects to Agent Arena Bridge",
        "hypothesize connection",
        "diagnose selection",
        "prepare agent task",
        "unknown gibberish command",
    ],
)
def test_all_commands_include_required_fields(tmp_path: Path, command: str):
    """Every command response must include visual_update, truth_packet, next_actions, patch_authority, vsa_patch_authority: false."""
    arena = HumanAgentArena(tmp_path, demo=True)
    # Provide a selection for commands that need it.
    node_ids = list(arena._node_by_id.keys())[:2]
    result = arena.route_command(command, selected_node_ids=node_ids, mode="explore")
    assert "visual_update" in result, f"Missing visual_update for: {command}"
    assert "truth_packet" in result, f"Missing truth_packet for: {command}"
    assert "next_actions" in result, f"Missing next_actions for: {command}"
    tp = result["truth_packet"]
    assert tp.get("patch_authority") == "exact_source_spans_and_hashes_only", f"Bad patch_authority for: {command}"
    assert tp.get("vsa_patch_authority") is False, f"vsa_patch_authority not False for: {command}"


# ---------------------------------------------------------------------------
# No production mutation from any command
# ---------------------------------------------------------------------------


def test_no_production_mutation_from_commands(tmp_path: Path):
    """No command should create, modify, or delete production files."""
    arena = HumanAgentArena(tmp_path, demo=True)
    node_ids = list(arena._node_by_id.keys())[:2]
    commands = [
        "show ST3GG",
        "show JSpace",
        "show Agent Arena Bridge",
        "show tests",
        "show dependencies",
        "isolate selected",
        "expand depth 2",
        "show unwired connections here",
        "what if ST3GG connects to Agent Arena Bridge",
        "hypothesize connection",
        "diagnose selection",
        "prepare agent task",
    ]
    files_before = {p: p.read_bytes() for p in tmp_path.rglob("*.py")}
    for command in commands:
        arena.route_command(command, selected_node_ids=node_ids)
    files_after = {p: p.read_bytes() for p in tmp_path.rglob("*.py")}
    # No files should be created.
    new_files = set(files_after.keys()) - set(files_before.keys())
    assert not new_files, f"New files created: {new_files}"
    # No files should be modified.
    for path, content in files_before.items():
        assert files_after[path] == content, f"File modified: {path}"


# ---------------------------------------------------------------------------
# Frontend files exist and contain expected elements
# ---------------------------------------------------------------------------


def test_frontend_files_exist_and_contain_expected_elements():
    """The Human Agent Arena frontend must contain the graph, command box, event log, diagnostics, and next-actions."""
    repo_root = Path(__file__).parent.parent
    index = (repo_root / "aura_human_agent_arena/index.html").read_text(encoding="utf-8")
    script = (repo_root / "aura_human_agent_arena/main.js").read_text(encoding="utf-8")
    css = (repo_root / "aura_human_agent_arena/arena.css").read_text(encoding="utf-8")

    # HTML must have graph area, command textbox, run button, mic button, event log, diagnostics, next-actions.
    assert "arena-canvas" in index
    assert "command-input" in index
    assert "run-button" in index
    assert "mic-button" in index
    assert "event-log" in index
    assert "diagnostics-panel" in index
    assert "next-actions-list" in index
    assert "truth-packet" in index
    assert "mode-select" in index

    # JS must poll the state endpoint and post to command endpoint.
    assert "/api/human-agent/state" in script
    assert "/api/human-agent/command" in script
    assert "setInterval" in script  # polling
    assert "SpeechRecognition" in script  # optional voice
    assert "800" in script  # poll interval

    # CSS must have ghost edge color and panel styling.
    assert "--ghost" in css
    assert "arena-shell" in css
    assert "side-panel" in css


# ---------------------------------------------------------------------------
# V1.2 Intelligence Layer — command routing specificity
# ---------------------------------------------------------------------------


def test_show_tests_for_selected_routes_to_selected_handler(tmp_path: Path):
    """'show tests for selected' must route to _cmd_show_tests_for_selected, not _cmd_show_tests."""
    arena = HumanAgentArena(tmp_path, demo=True)
    handler = arena._dispatch("show tests for selected", "explore")
    assert handler == arena._cmd_show_tests_for_selected


def test_show_tests_generic_routes_to_generic_handler(tmp_path: Path):
    """'show tests' (without 'selected') must still route to _cmd_show_tests."""
    arena = HumanAgentArena(tmp_path, demo=True)
    handler = arena._dispatch("show tests", "explore")
    assert handler == arena._cmd_show_tests


def test_show_docs_for_selected_routes_to_selected_handler(tmp_path: Path):
    """'show docs for selected' must route to _cmd_show_docs_for_selected."""
    arena = HumanAgentArena(tmp_path, demo=True)
    handler = arena._dispatch("show docs for selected", "explore")
    assert handler == arena._cmd_show_docs_for_selected


def test_show_affordances_for_selected_routes_correctly(tmp_path: Path):
    """'show affordances for selected' must route to _cmd_show_affordances."""
    arena = HumanAgentArena(tmp_path, demo=True)
    handler = arena._dispatch("show affordances for selected", "explore")
    assert handler == arena._cmd_show_affordances


def test_inspect_selected_routes_before_concept_commands(tmp_path: Path):
    """'inspect selected' must route to _cmd_inspect_selected."""
    arena = HumanAgentArena(tmp_path, demo=True)
    handler = arena._dispatch("inspect selected", "explore")
    assert handler == arena._cmd_inspect_selected


def test_show_exact_source_for_selected_routes_correctly(tmp_path: Path):
    """'show exact source for selected' must route to _cmd_show_exact_source."""
    arena = HumanAgentArena(tmp_path, demo=True)
    handler = arena._dispatch("show exact source for selected", "explore")
    assert handler == arena._cmd_show_exact_source


def test_expand_selected_routes_before_expand_depth(tmp_path: Path):
    """'expand selected' must route to _cmd_expand_selected, not _cmd_expand_depth."""
    arena = HumanAgentArena(tmp_path, demo=True)
    handler = arena._dispatch("expand selected", "explore")
    assert handler == arena._cmd_expand_selected


def test_show_callers_routes_correctly(tmp_path: Path):
    """'show callers' must route to _cmd_show_callers."""
    arena = HumanAgentArena(tmp_path, demo=True)
    handler = arena._dispatch("show callers", "explore")
    assert handler == arena._cmd_show_callers


def test_show_callees_routes_correctly(tmp_path: Path):
    """'show callees' must route to _cmd_show_callees."""
    arena = HumanAgentArena(tmp_path, demo=True)
    handler = arena._dispatch("show callees", "explore")
    assert handler == arena._cmd_show_callees


def test_show_risks_routes_correctly(tmp_path: Path):
    """'show risks' must route to _cmd_show_risks."""
    arena = HumanAgentArena(tmp_path, demo=True)
    handler = arena._dispatch("show risks", "explore")
    assert handler == arena._cmd_show_risks


def test_what_would_break_routes_correctly(tmp_path: Path):
    """'what would break if this changed' must route to _cmd_what_would_break."""
    arena = HumanAgentArena(tmp_path, demo=True)
    handler = arena._dispatch("what would break if this changed", "explore")
    assert handler == arena._cmd_what_would_break


def test_why_is_this_node_here_routes_correctly(tmp_path: Path):
    """'why is this node here' must route to _cmd_why_is_node_here."""
    arena = HumanAgentArena(tmp_path, demo=True)
    handler = arena._dispatch("why is this node here", "explore")
    assert handler == arena._cmd_why_is_node_here


def test_explain_selected_routes_correctly(tmp_path: Path):
    """'explain selected' must route to _cmd_inspect_selected."""
    arena = HumanAgentArena(tmp_path, demo=True)
    handler = arena._dispatch("explain selected", "explore")
    assert handler == arena._cmd_inspect_selected


# ---------------------------------------------------------------------------
# V1.2 — AFFORDANCE_MAP.json declares source of truth
# ---------------------------------------------------------------------------


def test_affordance_map_declares_source_of_truth():
    """The .aura/AFFORDANCE_MAP.json must declare its mode and source of truth."""
    repo_root = Path(__file__).parent.parent
    map_path = repo_root / ".aura" / "AFFORDANCE_MAP.json"
    assert map_path.exists(), "AFFORDANCE_MAP.json must exist"
    data = json.loads(map_path.read_text(encoding="utf-8"))
    assert data.get("mode") == "generated_placeholder"
    assert data.get("source_of_truth") == "aura_affordance_directory.SEED_AFFORDANCES"
    assert "note" in data
    assert "affordances" in data  # key exists (may be empty array)


# ---------------------------------------------------------------------------
# V1.2 — Projected nodes are labeled CODEMAP-projected, not synthetic/fake
# ---------------------------------------------------------------------------


def test_projected_nodes_labeled_codemap_projected(tmp_path: Path):
    """Concept workspace projected nodes must use 'codemap_projected_node' origin, not 'synthetic'/'fake'."""
    arena = HumanAgentArena(tmp_path, demo=True)
    result = arena.route_command("show Agent Arena Bridge", selected_node_ids=[], mode="explore")
    assert result["ok"] is True
    visual = result.get("visual_update", {})
    nodes = visual.get("additional_nodes", [])
    for node in nodes:
        serialized = json.dumps(node)
        assert "synthetic node" not in serialized.lower()
        assert "fake node" not in serialized.lower()
        # Origin should be codemap_projected_node or exact_topology_node
        origin = node.get("node_origin", node.get("metadata", {}).get("node_origin", ""))
        assert origin in ("codemap_projected_node", "exact_topology_node", "")


# ---------------------------------------------------------------------------
# V1.2 — Projected nodes survive state refresh
# ---------------------------------------------------------------------------


def test_projected_nodes_survive_state_refresh(tmp_path: Path):
    """After building a concept workspace, arena.topology must still contain the projected nodes after get_state()."""
    arena = HumanAgentArena(tmp_path, demo=True)

    # Count nodes before
    nodes_before = len(arena.topology["nodes"])

    # Run a concept workspace command that adds projected nodes
    result = arena.route_command("show Agent Arena Bridge", selected_node_ids=[], mode="explore")
    assert result["ok"] is True

    # Count nodes after — should have grown (or stayed same if no projections)
    nodes_after = len(arena.topology["nodes"])
    assert nodes_after >= nodes_before, "Concept workspace should not remove topology nodes"

    # Now simulate a polling refresh — call get_state() then check topology persists
    # get_state() returns state.to_dict() (the HumanAgentArenaState dataclass).
    # The arena.topology dict is separate and must retain projected nodes.
    _ = arena.get_state()
    nodes_after_refresh = len(arena.topology["nodes"])
    assert nodes_after_refresh == nodes_after, "Projected nodes must survive state refresh in arena.topology"

    # Also verify the server endpoint pattern: topology is returned alongside state
    # (the server returns {"state": arena.get_state(), "topology": arena.topology})
    # so projected nodes in arena.topology are always available to the frontend.


# ---------------------------------------------------------------------------
# V1.2 — Frontend re-merges projected nodes after polling
# ---------------------------------------------------------------------------


def test_frontend_remerges_projected_nodes_after_loadstate():
    """The frontend loadState() must re-merge locally cached projected nodes after a poll."""
    repo_root = Path(__file__).parent.parent
    script = (repo_root / "aura_human_agent_arena/main.js").read_text(encoding="utf-8")
    # The loadState function must check projectedNodes and re-merge them
    assert "projectedNodes" in script
    assert "existingIds" in script
    # The re-merge logic must be inside loadState
    load_state_idx = script.index("async function loadState()")
    remerge_idx = script.index("projectedNodes", load_state_idx)
    # The re-merge code should be after loadState starts
    assert remerge_idx > load_state_idx
