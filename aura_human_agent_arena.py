"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9f3-[Q-SYS:HUMAN_AGENT_ARENA]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Human-in-the-loop topology cockpit)
DEPENDENCIES: __future__, dataclasses, hashlib, pathlib, time, typing,
              aura_coding_arena_3d, aura_human_agent_concepts
FUNCTIONS: HumanAgentArenaState, HumanAgentArena, route_command, _truth_packet_base,
           _visual_update_base, build_concept_workspace, resolve_node_ref
SYNOPSIS: Additive third surface — a Jarvis-style human-in-the-loop topology cockpit.
Deterministic command router (no LLM). Reuses existing Coding Arena topology functions
read-only. Ghost edges live only in live state. Agent Arena Bridge is used only for
prepared handoff. No production code is mutated from voice or graph commands.
Concept Workspace upgrade (V1.1): commands like 'show Agent Arena Bridge' and
'show Coding Arena' now search the full CODEMAP index and synthesise ArenaNode-compatible
dicts for CODEMAP matches not present in the projected topology.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
from pathlib import Path
import time
from typing import Any, Iterable

from aura_coding_arena_3d import (
    detect_wiring_faults,
    load_arena_topology,
    select_micro_arena,
)

try:
    from aura_human_agent_concepts import (
        build_concept_workspace as _build_concept_workspace,
        resolve_node_ref as _resolve_node_ref_concepts,
        get_profile as _get_concept_profile,
        list_concept_keys as _list_concept_keys,
        ConceptWorkspace,
    )
    _CONCEPTS_AVAILABLE = True
except Exception:  # noqa: BLE001
    _CONCEPTS_AVAILABLE = False
    _build_concept_workspace = None  # type: ignore[assignment]
    _resolve_node_ref_concepts = None  # type: ignore[assignment]
    _get_concept_profile = None  # type: ignore[assignment]
    _list_concept_keys = None  # type: ignore[assignment]
    ConceptWorkspace = None  # type: ignore[assignment]


HUMAN_AGENT_ARENA_VERSION = "AURA_HUMAN_AGENT_ARENA_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

# Terms used to filter/highlight nodes for each "show <concept>" command.
# These legacy tuples are preserved for the fallback path when the concept
# engine is unavailable. New code goes through build_concept_workspace.
ST3GG_TERMS = ("st3gg", "arena_st3gg", "st3gg_codec", "st3gg_egress")
JSPACE_TERMS = ("jspace", "j_space", "jspace_codec", "jspace_packet", "jspace_state")
AGENT_ARENA_TERMS = ("aura_agent_arena", "agent_arena_bridge", "agent_arena_cli", "agent_arena_mcp")
TEST_PREFIX = "test_"


@dataclass
class GhostEdge:
    """A hypothesis edge stored only in live state. Never patch authority."""

    source: str
    target: str
    label: str = "ghost_hypothesis"
    hypothesis_id: str = ""
    created_at: float = 0.0
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class HumanAgentArenaState:
    """Minimal serializable live state for the Human Agent Arena cockpit.

    All fields are JSON-serializable. Ghost edges and hypotheses live here only —
    they are never written to topology, files, or patch authority.
    """

    visible_node_ids: list[str] = field(default_factory=list)
    hidden_node_ids: list[str] = field(default_factory=list)
    selected_node_ids: list[str] = field(default_factory=list)
    active_filter: str = ""
    micro_arena: dict[str, Any] = field(default_factory=dict)
    ghost_edges: list[dict[str, Any]] = field(default_factory=list)
    diagnostics: list[dict[str, Any]] = field(default_factory=list)
    hypotheses: list[dict[str, Any]] = field(default_factory=list)
    agent_tasks: list[dict[str, Any]] = field(default_factory=list)
    # Concept workspace — populated by show/refactor concept commands.
    concept_workspace: dict[str, Any] = field(default_factory=dict)
    # Stored handoff packets from prepare agent task (prevents silent loss).
    prepared_handoff_packets: list[dict[str, Any]] = field(default_factory=list)
    human_notes: list[str] = field(default_factory=list)
    event_log: list[dict[str, Any]] = field(default_factory=list)
    event_log_base_offset: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def add_event(self, kind: str, detail: str) -> None:
        self.event_log.append(
            {
                "ts": time.time(),
                "kind": str(kind),
                "detail": str(detail),
            }
        )
        # Cap event log to avoid unbounded growth while preserving absolute indexing.
        if len(self.event_log) > 500:
            removed = len(self.event_log) - 300
            self.event_log_base_offset += removed
            self.event_log = self.event_log[-300:]


class HumanAgentArena:
    """Deterministic command router for the Human Agent Arena.

    This is the third additive surface. It does NOT replace the CLI Coding Arena,
    the 3D Coding Arena, or the Agent Arena Bridge. It reuses existing topology
    functions read-only and routes human commands deterministically (no LLM).
    """

    def __init__(
        self,
        repo_root: str | Path = ".",
        *,
        demo: bool = False,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.demo = bool(demo)
        self.topology: dict[str, Any] = load_arena_topology(self.repo_root, demo=self.demo)
        self.state = HumanAgentArenaState()
        self._node_by_id: dict[str, dict[str, Any]] = {
            str(node.get("id")): node
            for node in self.topology.get("nodes", [])
            if isinstance(node, dict) and node.get("id")
        }
        self._all_node_ids: list[str] = list(self._node_by_id.keys())
        self.state.visible_node_ids = list(self._all_node_ids)
        self.state.add_event("init", f"Human Agent Arena started ({len(self._all_node_ids)} nodes)")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_state(self) -> dict[str, Any]:
        """Return the current live state as JSON-serializable dict."""
        return self.state.to_dict()

    def get_events(self, since: int = 0) -> dict[str, Any]:
        """Return events since the given absolute event index."""
        start_index = max(0, since - self.state.event_log_base_offset)
        events = self.state.event_log[start_index:]
        return {
            "ok": True,
            "events": events,
            "next_index": max(since, self.state.event_log_base_offset) + len(events),
            "total_events": self.state.event_log_base_offset + len(self.state.event_log),
        }

    def route_command(
        self,
        command: str,
        *,
        selected_node_ids: list[str] | None = None,
        mode: str = "explore",
    ) -> dict[str, Any]:
        """Route a human command deterministically.

        Returns:
            {
                "ok": True,
                "answer": str,
                "visual_update": {...},
                "truth_packet": {...},
                "next_actions": [...],
            }
        """
        command_text = str(command or "").strip()
        mode = str(mode or "explore").strip()
        if selected_node_ids is not None:
            self.state.selected_node_ids = [str(n) for n in selected_node_ids if n]
        self.state.add_event("command", f"[{mode}] {command_text}")

        handler = self._dispatch(command_text, mode)
        try:
            result = handler(command_text, mode)
        except Exception as exc:  # noqa: BLE001
            result = self._error_result(command_text, str(exc))
        # Ensure invariant fields are always present.
        result.setdefault("ok", True)
        result.setdefault("answer", "")
        result.setdefault("visual_update", _visual_update_base())
        result.setdefault("truth_packet", _truth_packet_base())
        result.setdefault("next_actions", [])
        # Enforce patch authority invariant on every response.
        result["truth_packet"]["patch_authority"] = PATCH_AUTHORITY
        result["truth_packet"]["vsa_patch_authority"] = VSA_PATCH_AUTHORITY
        return result

    # ------------------------------------------------------------------
    # Command dispatch
    # ------------------------------------------------------------------

    def _dispatch(self, command: str, mode: str):
        lowered = command.lower()

        # --------------- concept workspace commands (new in V1.1) ---------------
        # "show all functions related to <concept>" / "show functions for <concept>"
        if "show" in lowered and ("all function" in lowered or "function" in lowered) and (
            "related" in lowered or "for" in lowered
        ):
            return self._cmd_show_concept_functions
        # "show everything connected to <concept>"
        if "show" in lowered and "everything" in lowered and "connect" in lowered:
            return self._cmd_show_concept_full
        # "refactor <concept>" / "I want to refactor"
        if ("refactor" in lowered or "i want to refactor" in lowered) and mode != "prepare":
            return self._cmd_refactor_concept
        # "export handoff packet"
        if "export" in lowered and "handoff" in lowered:
            return self._cmd_export_handoff_packet
        # "prepare refactor plan"
        if "prepare" in lowered and "refactor" in lowered:
            return self._cmd_refactor_concept
        # --------------- existing concept show commands (now concept-workspace backed) ---------------
        # show ST3GG
        if "show" in lowered and "st3gg" in lowered:
            return self._cmd_show_st3gg
        # show JSpace
        if "show" in lowered and "jspace" in lowered:
            return self._cmd_show_jspace
        # show Agent Arena Bridge
        if "show" in lowered and ("agent arena" in lowered or "agent_arena" in lowered):
            return self._cmd_show_agent_arena
        # show Coding Arena
        if "show" in lowered and "coding arena" in lowered:
            return self._cmd_show_coding_arena
        # show <any known concept>
        if "show" in lowered and _CONCEPTS_AVAILABLE and _list_concept_keys is not None:
            for key in _list_concept_keys():
                if key.replace("_", " ") in lowered or key in lowered:
                    return self._cmd_show_generic_concept
        # --------------- existing commands ---------------
        # show tests
        if "show" in lowered and "test" in lowered:
            return self._cmd_show_tests
        # show dependencies
        if "show" in lowered and "depend" in lowered:
            return self._cmd_show_dependencies
        # isolate selected
        if "isolate" in lowered and ("select" in lowered or mode == "diagnose"):
            return self._cmd_isolate_selected
        # expand depth N
        if "expand" in lowered and "depth" in lowered:
            return self._cmd_expand_depth
        # show unwired connections here
        if ("unwired" in lowered and "connect" in lowered) or "unwired connections" in lowered:
            return self._cmd_show_unwired_connections
        # what if connect / source to target
        if ("what if" in lowered and "connect" in lowered) or (
            "what if" in lowered and "source" in lowered and "target" in lowered
        ) or ("what if" in lowered):
            return self._cmd_what_if_connect
        # hypothesize connection
        if "hypothes" in lowered and "connect" in lowered:
            return self._cmd_hypothesize_connection
        # diagnose selection
        if "diagnose" in lowered and ("select" in lowered or mode == "diagnose"):
            return self._cmd_diagnose_selection
        # prepare agent task
        if "prepare" in lowered and ("agent" in lowered or "task" in lowered or mode == "prepare"):
            return self._cmd_prepare_agent_task

        return self._cmd_unknown

    # ------------------------------------------------------------------
    # Command handlers
    # ------------------------------------------------------------------

    def _cmd_show_st3gg(self, command: str, mode: str) -> dict[str, Any]:
        return self._show_concept_workspace(command, mode, "st3gg", fallback_terms=ST3GG_TERMS)

    def _cmd_show_jspace(self, command: str, mode: str) -> dict[str, Any]:
        return self._show_concept_workspace(command, mode, "jspace", fallback_terms=JSPACE_TERMS)

    def _cmd_show_agent_arena(self, command: str, mode: str) -> dict[str, Any]:
        return self._show_concept_workspace(command, mode, "agent_arena_bridge", fallback_terms=AGENT_ARENA_TERMS)

    def _cmd_show_coding_arena(self, command: str, mode: str) -> dict[str, Any]:
        return self._show_concept_workspace(command, mode, "coding_arena")

    def _cmd_show_generic_concept(self, command: str, mode: str) -> dict[str, Any]:
        """Route 'show <any concept>' to the concept workspace engine."""
        return self._show_concept_workspace(command, mode, command)

    def _cmd_show_concept_functions(self, command: str, mode: str) -> dict[str, Any]:
        """Show all function/symbol nodes for a concept."""
        return self._show_concept_workspace(command, mode, command, ws_mode="functions")

    def _cmd_show_concept_full(self, command: str, mode: str) -> dict[str, Any]:
        """Show everything connected to a concept (neighbors, tests, docs, commands)."""
        return self._show_concept_workspace(command, mode, command, ws_mode="full")

    def _cmd_refactor_concept(self, command: str, mode: str) -> dict[str, Any]:
        """Build a concept workspace in prepare mode and suggest refactor next actions."""
        ws_result = self._show_concept_workspace(command, mode, command, ws_mode="prepare")
        # Override next_actions to include refactor suggestions.
        ws_result["next_actions"] = [
            "diagnose selection",
            "show tests",
            "show unwired connections here",
            "prepare agent task",
        ]
        ws_result["answer"] = (
            f"Concept workspace built for refactor. {ws_result.get('answer', '')} "
            "Review the workspace, diagnose selection, then prepare agent task when ready."
        )
        return ws_result

    def _cmd_export_handoff_packet(self, command: str, mode: str) -> dict[str, Any]:
        """Export the current concept workspace + plan summary as JSON."""
        packets = self.state.prepared_handoff_packets
        workspace = self.state.concept_workspace
        workspace_id = workspace.get("workspace_id", _short_hash(str(time.time()), size=8))
        export_payload = {
            "export_version": HUMAN_AGENT_ARENA_VERSION,
            "workspace_id": workspace_id,
            "concept_workspace": workspace,
            "prepared_handoff_packets": packets[-3:] if packets else [],
            "selected_node_ids": list(self.state.selected_node_ids),
            "exported_at": time.time(),
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            "note": "This packet is for human review and agent handoff only. No production mutation.",
        }
        # Optionally write to Aura_Memory
        try:
            mem_dir = self.repo_root / "Aura_Memory" / "human_agent_arena"
            mem_dir.mkdir(parents=True, exist_ok=True)
            out_path = mem_dir / f"handoff_{workspace_id}.json"
            import json as _json
            out_path.write_text(
                _json.dumps(export_payload, indent=2, default=str),
                encoding="utf-8",
            )
            export_note = f"Exported to {out_path}"
        except Exception as exc:  # noqa: BLE001
            out_path = None
            export_note = f"Memory write skipped ({exc}); returning JSON only."
        self.state.add_event("export_handoff", export_note)
        truth = _truth_packet_base()
        truth["workspace_id"] = workspace_id
        truth["concept"] = workspace.get("concept", "")
        truth["files"] = workspace.get("files", [])
        truth["symbols"] = workspace.get("symbols", [])
        truth["grounding"] = "grounded" if workspace else "NEEDS_GROUNDING"
        truth["note"] = export_note
        return {
            "ok": True,
            "answer": f"Handoff packet exported. {export_note}",
            "visual_update": _visual_update_base(),
            "truth_packet": truth,
            "handoff_packet": export_payload,
            "next_actions": [
                "diagnose selection",
                "prepare agent task",
            ],
        }

    def _cmd_show_tests(self, command: str, mode: str) -> dict[str, Any]:
        """Highlight known test files connected to the current selection."""
        selected = self.state.selected_node_ids
        test_nodes = self._find_test_nodes(selected)
        highlighted = [node_id for node_id in test_nodes if node_id in self._node_by_id]
        hidden = [nid for nid in self._all_node_ids if nid not in highlighted and nid not in selected]
        self.state.active_filter = "tests"
        self.state.visible_node_ids = [*highlighted, *selected]
        self.state.hidden_node_ids = hidden
        self.state.add_event("filter", f"show tests: {len(highlighted)} highlighted")

        truth = _truth_packet_base()
        truth["files"] = sorted(
            {str(self._node_by_id[nid].get("file_path", "")) for nid in highlighted if nid in self._node_by_id}
        )
        truth["symbols"] = sorted(
            {str(self._node_by_id[nid].get("symbol", "")) for nid in highlighted if nid in self._node_by_id}
        )
        truth["tests"] = list(truth["files"])
        truth["grounding"] = "grounded" if highlighted else "NEEDS_GROUNDING"

        return {
            "ok": True,
            "answer": f"Highlighted {len(highlighted)} test node(s) connected to selection.",
            "visual_update": {
                "highlighted_node_ids": highlighted,
                "hidden_node_ids": hidden,
                "selected_node_ids": selected,
                "ghost_edges": [ge for ge in self.state.ghost_edges],
                "labels": {nid: "test" for nid in highlighted},
                "ui_hints": ["test_filter_active"],
            },
            "truth_packet": truth,
            "next_actions": [
                "diagnose selection",
                "show dependencies",
                "prepare agent task",
            ],
        }

    def _cmd_show_dependencies(self, command: str, mode: str) -> dict[str, Any]:
        """Show dependency neighbors of the current selection."""
        selected = self.state.selected_node_ids
        if not selected:
            return self._no_selection_result("show dependencies")
        micro = select_micro_arena(self.topology, selected, depth=1, human_instruction=command)
        deps = micro.get("dependencies", []) or []
        dep_ids = [str(d.get("id", "")) for d in deps if d.get("id")]
        highlighted = [nid for nid in dep_ids if nid in self._node_by_id]
        hidden = [nid for nid in self._all_node_ids if nid not in highlighted and nid not in selected]
        self.state.active_filter = "dependencies"
        self.state.visible_node_ids = [*highlighted, *selected]
        self.state.hidden_node_ids = hidden
        self.state.micro_arena = micro
        self.state.add_event("filter", f"show dependencies: {len(highlighted)} nodes")

        truth = _truth_packet_base()
        truth["files"] = sorted(
            {str(d.get("file_path", "")) for d in deps if d.get("file_path")}
        )
        truth["symbols"] = sorted(
            {str(d.get("symbol", "")) for d in deps if d.get("symbol")}
        )
        truth["line_ranges"] = [
            {
                "node_id": str(d.get("id", "")),
                "file_path": str(d.get("file_path", "")),
                "symbol": str(d.get("symbol", "")),
            }
            for d in deps
            if d.get("id")
        ]
        truth["grounding"] = "grounded" if deps else "NEEDS_GROUNDING"

        return {
            "ok": True,
            "answer": f"Found {len(highlighted)} dependency neighbor(s) for selection.",
            "visual_update": {
                "highlighted_node_ids": highlighted,
                "hidden_node_ids": hidden,
                "selected_node_ids": selected,
                "ghost_edges": [ge for ge in self.state.ghost_edges],
                "labels": {nid: "dependency" for nid in highlighted},
                "ui_hints": ["dependency_filter_active"],
            },
            "truth_packet": truth,
            "next_actions": [
                "expand depth 2",
                "diagnose selection",
                "show tests",
            ],
        }

    def _cmd_isolate_selected(self, command: str, mode: str) -> dict[str, Any]:
        """Isolate a micro-arena around the current selection."""
        selected = self.state.selected_node_ids
        if not selected:
            return self._no_selection_result("isolate selected")
        micro = select_micro_arena(self.topology, selected, depth=1, human_instruction=command)
        micro_node_ids = [str(n.get("id", "")) for n in micro.get("nodes", []) if n.get("id")]
        hidden = [nid for nid in self._all_node_ids if nid not in micro_node_ids]
        self.state.active_filter = "micro_arena"
        self.state.visible_node_ids = micro_node_ids
        self.state.hidden_node_ids = hidden
        self.state.micro_arena = micro
        self.state.add_event("isolate", f"isolated {len(micro_node_ids)} nodes")

        truth = _truth_packet_from_micro(micro)
        return {
            "ok": True,
            "answer": f"Isolated micro-arena with {len(micro_node_ids)} node(s).",
            "visual_update": {
                "highlighted_node_ids": micro_node_ids,
                "hidden_node_ids": hidden,
                "selected_node_ids": selected,
                "ghost_edges": [ge for ge in self.state.ghost_edges],
                "labels": {},
                "ui_hints": ["micro_arena_isolated"],
            },
            "truth_packet": truth,
            "next_actions": [
                "diagnose selection",
                "show unwired connections here",
                "prepare agent task",
            ],
        }

    def _cmd_expand_depth(self, command: str, mode: str) -> dict[str, Any]:
        """Expand the selection to a given depth."""
        selected = self.state.selected_node_ids
        if not selected:
            return self._no_selection_result("expand depth")
        depth = _parse_depth(command, default=2)
        micro = select_micro_arena(self.topology, selected, depth=depth, human_instruction=command)
        micro_node_ids = [str(n.get("id", "")) for n in micro.get("nodes", []) if n.get("id")]
        hidden = [nid for nid in self._all_node_ids if nid not in micro_node_ids]
        self.state.active_filter = f"expand_depth_{depth}"
        self.state.visible_node_ids = micro_node_ids
        self.state.hidden_node_ids = hidden
        self.state.micro_arena = micro
        self.state.add_event("expand", f"expanded to depth {depth}: {len(micro_node_ids)} nodes")

        truth = _truth_packet_from_micro(micro)
        truth["depth"] = depth
        return {
            "ok": True,
            "answer": f"Expanded selection to depth {depth}: {len(micro_node_ids)} node(s).",
            "visual_update": {
                "highlighted_node_ids": micro_node_ids,
                "hidden_node_ids": hidden,
                "selected_node_ids": selected,
                "ghost_edges": [ge for ge in self.state.ghost_edges],
                "labels": {},
                "ui_hints": [f"depth_{depth}"],
            },
            "truth_packet": truth,
            "next_actions": [
                "isolate selected",
                "diagnose selection",
                "show dependencies",
            ],
        }

    def _cmd_show_unwired_connections(self, command: str, mode: str) -> dict[str, Any]:
        """Call or adapt the read-only emergent potential audit, scoped to selection."""
        selected = self.state.selected_node_ids
        truth = _truth_packet_base()

        # Try the read-only emergent potential audit.
        try:
            from aura_emergent_potential_repl import audit_emergent_potential

            report = audit_emergent_potential(
                self.repo_root,
                top=8,
                focus=" ".join(self._selected_file_names(selected)) or "unwired",
            )
            report_dict = report.to_dict()
            connections = report_dict.get("connections", []) or []
            # Extract source/target file info from connections.
            unwired = []
            for conn in connections[:8]:
                src = conn.get("source", {}) or {}
                tgt = conn.get("target", {}) or {}
                unwired.append(
                    {
                        "source_file": str(src.get("file", "")),
                        "source_symbol": str(src.get("symbol", "")),
                        "target_file": str(tgt.get("file", "")),
                        "target_symbol": str(tgt.get("symbol", "")),
                        "missing_wire": str(conn.get("missing_wire", "")),
                        "status": str(conn.get("status", "NEEDS_GROUNDING")),
                        "emergence_score": float(conn.get("emergence_score", 0.0)),
                    }
                )
            truth["files"] = sorted(
                {item for c in unwired for item in (c["source_file"], c["target_file"]) if item}
            )
            truth["symbols"] = sorted(
                {item for c in unwired for item in (c["source_symbol"], c["target_symbol"]) if item}
            )
            truth["unwired_connections"] = unwired
            truth["grounding"] = "grounded" if unwired else "NEEDS_GROUNDING"
            truth["read_only"] = True
            truth["constraints"] = list(report_dict.get("constraints", []))

            self.state.add_event("audit", f"unwired connections: {len(unwired)} candidates")
            return {
                "ok": True,
                "answer": f"Found {len(unwired)} unwired connection candidate(s) (read-only audit).",
                "visual_update": {
                    "highlighted_node_ids": self._node_ids_for_files(truth["files"]),
                    "hidden_node_ids": [],
                    "selected_node_ids": selected,
                    "ghost_edges": [ge for ge in self.state.ghost_edges],
                    "labels": {},
                    "ui_hints": ["unwired_audit_complete"],
                },
                "truth_packet": truth,
                "next_actions": [
                    "hypothesize connection",
                    "diagnose selection",
                    "prepare agent task",
                ],
            }
        except Exception:  # noqa: BLE001
            # MVP fallback: return selected files with NEEDS_GROUNDING note.
            selected_files = self._selected_file_names(selected)
            truth["files"] = sorted(set(selected_files))
            truth["symbols"] = []
            truth["unwired_connections"] = []
            truth["grounding"] = "NEEDS_GROUNDING"
            truth["read_only"] = True
            truth["constraints"] = ["NO_PATCHES", "NO_CODE_WRITES", "REPORT_ONLY"]
            truth["note"] = (
                "Scoped emergent potential audit unavailable in this environment. "
                "Showing current selected files as MVP fallback. Marked NEEDS_GROUNDING."
            )
            self.state.add_event("audit_fallback", "unwired connections: NEEDS_GROUNDING fallback")
            return {
                "ok": True,
                "answer": (
                    "Unwired connections audit fell back to MVP mode. "
                    "Selected files shown; marked NEEDS_GROUNDING."
                ),
                "visual_update": {
                    "highlighted_node_ids": selected,
                    "hidden_node_ids": [],
                    "selected_node_ids": selected,
                    "ghost_edges": [ge for ge in self.state.ghost_edges],
                    "labels": {},
                    "ui_hints": ["unwired_audit_fallback", "needs_grounding"],
                },
                "truth_packet": truth,
                "next_actions": [
                    "hypothesize connection",
                    "diagnose selection",
                    "prepare agent task",
                ],
            }

    def _cmd_what_if_connect(self, command: str, mode: str) -> dict[str, Any]:
        """Parse 'what if <source> connects to <target>' and create a ghost edge only."""
        source, target = _parse_what_if(command)
        if not source or not target:
            # Try to use selected nodes.
            selected = self.state.selected_node_ids
            if len(selected) >= 2:
                source = source or selected[0]
                target = target or selected[1]
        if not source or not target:
            return {
                "ok": True,
                "answer": "Need a source and target. Try: 'what if ST3GG connects to Agent Arena Bridge'.",
                "visual_update": _visual_update_base(),
                "truth_packet": _truth_packet_base_needs_grounding(),
                "next_actions": ["show ST3GG", "show Agent Arena Bridge", "hypothesize connection"],
            }
        ghost = self._add_ghost_edge(source, target, note=command)
        truth = _truth_packet_base()
        truth["files"] = sorted(
            {
                str(self._node_by_id.get(source, {}).get("file_path", "")),
                str(self._node_by_id.get(target, {}).get("file_path", "")),
            }
        )
        truth["grounding"] = "NEEDS_GROUNDING"
        truth["note"] = "Ghost edge is a hypothesis only. Not patch authority. No code written."
        return {
            "ok": True,
            "answer": (
                f"Ghost edge created: {source} -> {target}. "
                "This is a hypothesis only — no code was written."
            ),
            "visual_update": {
                "highlighted_node_ids": [source, target],
                "hidden_node_ids": [],
                "selected_node_ids": [source, target],
                "ghost_edges": [ge for ge in self.state.ghost_edges],
                "labels": {source: "ghost_source", target: "ghost_target"},
                "ui_hints": ["ghost_edge_added"],
            },
            "truth_packet": truth,
            "next_actions": [
                "diagnose selection",
                "show unwired connections here",
                "prepare agent task",
            ],
        }

    def _cmd_hypothesize_connection(self, command: str, mode: str) -> dict[str, Any]:
        """Create a ghost edge only. Do not write code."""
        selected = self.state.selected_node_ids
        source, target = _parse_hypothesize(command)
        if not source or not target:
            if len(selected) >= 2:
                source = source or selected[0]
                target = target or selected[1]
            elif len(selected) == 1:
                source = source or selected[0]
        if not source or not target:
            return {
                "ok": True,
                "answer": "Need a source and target to hypothesize a connection.",
                "visual_update": _visual_update_base(),
                "truth_packet": _truth_packet_base_needs_grounding(),
                "next_actions": ["show ST3GG", "show Agent Arena Bridge", "what if connect source to target"],
            }
        ghost = self._add_ghost_edge(source, target, note=command)
        self.state.hypotheses.append(
            {
                "hypothesis_id": ghost["hypothesis_id"],
                "source": source,
                "target": target,
                "note": command,
                "created_at": ghost["created_at"],
            }
        )
        truth = _truth_packet_base()
        truth["files"] = sorted(
            {
                str(self._node_by_id.get(source, {}).get("file_path", "")),
                str(self._node_by_id.get(target, {}).get("file_path", "")),
            }
        )
        truth["grounding"] = "NEEDS_GROUNDING"
        truth["note"] = "Hypothesis edge only. Not patch authority. No code written."
        return {
            "ok": True,
            "answer": (
                f"Hypothesis edge created: {source} -> {target}. "
                "No code written. Use 'prepare agent task' to hand off."
            ),
            "visual_update": {
                "highlighted_node_ids": [source, target],
                "hidden_node_ids": [],
                "selected_node_ids": [source, target],
                "ghost_edges": [ge for ge in self.state.ghost_edges],
                "labels": {source: "hypothesis_source", target: "hypothesis_target"},
                "ui_hints": ["hypothesis_edge_added"],
            },
            "truth_packet": truth,
            "next_actions": [
                "diagnose selection",
                "show unwired connections here",
                "prepare agent task",
            ],
        }

    def _cmd_diagnose_selection(self, command: str, mode: str) -> dict[str, Any]:
        """Run wiring fault diagnostics on the current selection."""
        selected = self.state.selected_node_ids
        if not selected:
            return self._no_selection_result("diagnose selection")
        faults = detect_wiring_faults(self.topology, selected, depth=1)
        fault_dicts = [f.to_dict() for f in faults]
        self.state.diagnostics = fault_dicts
        self.state.add_event("diagnose", f"{len(fault_dicts)} fault(s) found")

        truth = _truth_packet_base()
        truth["files"] = sorted(
            {str(self._node_by_id.get(nid, {}).get("file_path", "")) for nid in selected if nid in self._node_by_id}
        )
        truth["symbols"] = sorted(
            {str(self._node_by_id.get(nid, {}).get("symbol", "")) for nid in selected if nid in self._node_by_id}
        )
        truth["line_ranges"] = [
            {
                "node_id": nid,
                "file_path": str(self._node_by_id.get(nid, {}).get("file_path", "")),
                "symbol": str(self._node_by_id.get(nid, {}).get("symbol", "")),
                "line_range": list(self._node_by_id.get(nid, {}).get("line_range", [])),
            }
            for nid in selected
            if nid in self._node_by_id
        ]
        truth["tests"] = self._find_test_files(selected)
        truth["diagnostics"] = fault_dicts
        truth["grounding"] = "grounded" if selected else "NEEDS_GROUNDING"

        return {
            "ok": True,
            "answer": (
                f"Diagnosed selection: {len(fault_dicts)} wiring fault(s) found. "
                + ("No high-severity faults." if not any(f.get("severity") == "high" for f in fault_dicts) else "High-severity faults present — review before patching.")
            ),
            "visual_update": {
                "highlighted_node_ids": selected,
                "hidden_node_ids": [],
                "selected_node_ids": selected,
                "ghost_edges": [ge for ge in self.state.ghost_edges],
                "labels": {nid: "diagnosed" for nid in selected},
                "ui_hints": ["diagnostics_complete"],
            },
            "truth_packet": truth,
            "next_actions": [
                "show tests",
                "show unwired connections here",
                "prepare agent task",
            ],
        }

    def _cmd_prepare_agent_task(self, command: str, mode: str) -> dict[str, Any]:
        """Call AuraAgentArenaBridge.aura_prepare_arena only after building an objective."""
        selected = self.state.selected_node_ids
        objective = _build_objective(command, selected, self._node_by_id)
        if not objective.strip():
            # Try building objective from current concept workspace
            ws = self.state.concept_workspace
            if ws.get("concept"):
                objective = f"Prepare agent task for concept: {ws['concept']}"
        if not objective.strip():
            return {
                "ok": True,
                "answer": "Need an objective or selection to prepare an agent task.",
                "visual_update": _visual_update_base(),
                "truth_packet": _truth_packet_base_needs_grounding(),
                "next_actions": ["show ST3GG", "diagnose selection", "isolate selected"],
            }

        target_file = None
        target_symbol = None
        if selected:
            node = self._node_by_id.get(selected[0], {})
            target_file = str(node.get("file_path", "")) or None
            target_symbol = str(node.get("symbol", "")) or None

        workspace_id = self.state.concept_workspace.get("workspace_id", "")

        try:
            from aura_agent_arena_bridge import AuraAgentArenaBridge

            bridge = AuraAgentArenaBridge(repo_root=self.repo_root)
            prepared = bridge.aura_prepare_arena(
                objective=objective,
                target_file=target_file,
                target_symbol=target_symbol,
            )
        except Exception as exc:  # noqa: BLE001
            truth = _truth_packet_base_needs_grounding()
            truth["note"] = f"Agent Arena Bridge prepare failed: {exc}"
            self.state.add_event("prepare_failed", str(exc))
            return {
                "ok": True,
                "answer": f"Agent task preparation failed: {exc}. No production files mutated.",
                "visual_update": _visual_update_base(),
                "truth_packet": truth,
                "next_actions": ["diagnose selection", "show dependencies", "isolate selected"],
            }

        plan_phase_hash = str(prepared.get("plan_phase_hash", ""))
        # Build and store handoff packet so it is never silently lost.
        handoff_packet: dict[str, Any] = {
            "objective": objective,
            "plan_phase_hash": plan_phase_hash,
            "target_file": target_file,
            "target_symbol": target_symbol,
            "selected_node_ids": list(selected),
            "workspace_id": workspace_id,
            "recommended_next_cli_commands": [
                f"python aura_agent_arena_cli.py prepare --objective \"{objective}\"",
            ],
            "prepared_at": time.time(),
            "note": (
                "If an external Agent Arena Bridge process needs to continue, "
                "re-run aura_prepare_arena using the objective and target, unless "
                "persistent bridge sessions are implemented."
            ),
        }
        self.state.prepared_handoff_packets.append(handoff_packet)

        # Store the prepared task in live state.
        task_entry = {
            "objective": objective,
            "target_file": target_file,
            "target_symbol": target_symbol,
            "plan_phase_hash": plan_phase_hash,
            "blockers": list(prepared.get("blockers", [])),
            "warnings": list(prepared.get("warnings", [])),
            "prepared_at": time.time(),
        }
        self.state.agent_tasks.append(task_entry)
        self.state.add_event("prepare", f"agent task prepared: {plan_phase_hash}")

        truth = _truth_packet_base()
        truth["concept"] = self.state.concept_workspace.get("concept", "")
        truth["workspace_id"] = workspace_id
        truth["files"] = sorted({target_file} if target_file else set())
        truth["symbols"] = sorted({target_symbol} if target_symbol else set())
        truth["plan_phase_hash"] = plan_phase_hash
        truth["act_capsules"] = list(prepared.get("act_capsules", []))
        truth["grounding_evidence"] = list(prepared.get("grounding_evidence", []))
        truth["shadow_findings"] = list(prepared.get("shadow_findings", []))
        truth["routing_decisions"] = list(prepared.get("routing_decisions", []))
        truth["blockers"] = list(prepared.get("blockers", []))
        truth["warnings"] = list(prepared.get("warnings", []))
        truth["grounding"] = "grounded" if prepared.get("ok") else "NEEDS_GROUNDING"

        return {
            "ok": True,
            "answer": (
                f"Agent task prepared. Plan phase hash: {plan_phase_hash}. "
                f"{len(truth['blockers'])} blocker(s), {len(truth['warnings'])} warning(s). "
                "No production files mutated. Handoff ready for Agent Arena Bridge."
            ),
            "visual_update": {
                "highlighted_node_ids": selected,
                "hidden_node_ids": [],
                "selected_node_ids": selected,
                "ghost_edges": [ge for ge in self.state.ghost_edges],
                "labels": {nid: "prepared" for nid in selected},
                "ui_hints": ["agent_task_prepared", "handoff_ready"],
            },
            "truth_packet": truth,
            "handoff_packet": handoff_packet,
            "next_actions": [
                "diagnose selection",
                "show tests",
                "show unwired connections here",
                "export handoff packet",
            ],
        }

    def _cmd_unknown(self, command: str, mode: str) -> dict[str, Any]:
        """Fallback for unrecognized commands."""
        self.state.add_event("unknown", command)
        return {
            "ok": True,
            "answer": (
                "Unknown command. Try: show ST3GG, show JSpace, show Agent Arena Bridge, "
                "show tests, show dependencies, isolate selected, expand depth 2, "
                "show unwired connections here, what if connect source to target, "
                "hypothesize connection, diagnose selection, prepare agent task."
            ),
            "visual_update": _visual_update_base(),
            "truth_packet": _truth_packet_base_needs_grounding(),
            "next_actions": [
                "show ST3GG",
                "show JSpace",
                "show Agent Arena Bridge",
                "diagnose selection",
                "prepare agent task",
            ],
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _show_concept_workspace(
        self,
        command: str,
        mode: str,
        concept_or_query: str,
        *,
        fallback_terms: tuple[str, ...] | None = None,
        ws_mode: str = "explore",
    ) -> dict[str, Any]:
        """Build a concept workspace from CODEMAP and inject synthetic nodes into the visual update.

        This is the primary concept command handler in V1.1. It searches the full CODEMAP
        index (not only the projected topology) and synthesises ArenaNode-compatible dicts
        for CODEMAP matches not present in the projected topology.

        Falls back gracefully to the legacy _show_concept keyword filter if the concept
        engine is unavailable.
        """
        if not _CONCEPTS_AVAILABLE or _build_concept_workspace is None:
            # Legacy fallback: keyword filter over projected nodes only.
            terms = fallback_terms or (concept_or_query.lower(),)
            concept_name = concept_or_query
            return self._show_concept(command, mode, terms, concept_name)

        # Build concept workspace from full CODEMAP
        try:
            ws: ConceptWorkspace = _build_concept_workspace(
                concept_or_query,
                repo_root=self.repo_root,
                selected_node_ids=list(self.state.selected_node_ids),
                existing_nodes=self._node_by_id,
                depth=1,
                max_files=80,
                max_symbols=200,
                mode=ws_mode,
            )
        except Exception as exc:  # noqa: BLE001
            # Fallback to keyword filter
            terms = fallback_terms or (concept_or_query.lower(),)
            return self._show_concept(command, mode, terms, concept_or_query)

        concept_name = ws.concept
        profile_key = ws.profile_key

        # Collect existing projected nodes that match
        existing_highlighted: list[str] = []
        all_file_paths = set(ws.files)
        all_symbols = set(ws.symbols)
        for nid, node in self._node_by_id.items():
            fp = str(node.get("file_path", ""))
            sym = str(node.get("symbol", ""))
            if fp in all_file_paths or sym in all_symbols:
                existing_highlighted.append(nid)

        # Inject synthetic nodes into topology in-memory (visual advisory only)
        synthetic_nodes = [
            n for n in ws.nodes
            if n.get("metadata", {}).get("projected_from_codemap")
        ]
        # Add synthetic nodes to _node_by_id transiently (this session only, never persisted)
        synthetic_ids: list[str] = []
        for snode in synthetic_nodes:
            sid = str(snode["id"])
            if sid not in self._node_by_id:
                self._node_by_id[sid] = snode
                self._all_node_ids.append(sid)
            synthetic_ids.append(sid)

        # Build full highlighted list = existing matches + synthetic
        highlighted_set = set(existing_highlighted) | set(synthetic_ids)
        highlighted = list(highlighted_set)
        hidden = [nid for nid in self._all_node_ids if nid not in highlighted_set]

        self.state.active_filter = profile_key
        self.state.visible_node_ids = highlighted
        self.state.hidden_node_ids = hidden
        self.state.concept_workspace = {
            "concept": concept_name,
            "profile_key": profile_key,
            "workspace_id": ws.workspace_id,
            "files": ws.files,
            "symbols": ws.symbols,
            "docs": ws.docs,
            "tests": ws.tests,
            "commands": ws.commands,
            "neighbors": ws.neighbors,
            "token_estimates": ws.token_estimates,
            "grounding": ws.grounding,
        }
        self.state.add_event(
            "concept_workspace",
            f"{concept_name}: {len(highlighted)} nodes ({len(synthetic_ids)} synthetic from CODEMAP)",
        )

        truth = ws.to_truth_packet()
        truth["line_ranges"] = [
            {
                "node_id": nid,
                "file_path": str(self._node_by_id.get(nid, {}).get("file_path", "")),
                "symbol": str(self._node_by_id.get(nid, {}).get("symbol", "")),
                "line_range": list(self._node_by_id.get(nid, {}).get("line_range", [])),
            }
            for nid in existing_highlighted
            if self._node_by_id.get(nid, {}).get("line_range")
        ]

        visual_update = ws.to_visual_update(
            existing_node_ids=set(self._all_node_ids),
            selected_node_ids=self.state.selected_node_ids,
            current_ghost_edges=self.state.ghost_edges,
        )
        # Merge synthetic node canvas data into topology links for rendering
        visual_update["highlighted_node_ids"] = highlighted
        visual_update["hidden_node_ids"] = hidden

        # Determine next_actions based on mode
        if ws_mode == "prepare":
            next_actions = ["diagnose selection", "show tests", "show unwired connections here", "prepare agent task"]
        elif ws_mode == "functions":
            next_actions = ["diagnose selection", "isolate selected", "prepare agent task"]
        elif ws_mode == "full":
            next_actions = ["isolate selected", "diagnose selection", "prepare agent task", "export handoff packet"]
        else:
            next_actions = [
                "show all functions",
                "show neighbors",
                "show tests",
                "diagnose selection",
                "prepare agent task",
            ]

        return {
            "ok": True,
            "answer": (
                f"Concept workspace '{concept_name}': {len(ws.files)} file(s), "
                f"{len(ws.symbols)} symbol(s), {len(ws.tests)} test(s), "
                f"{len(ws.docs)} doc(s). "
                f"{len(synthetic_ids)} node(s) synthesised from CODEMAP (visual-only)."
            ),
            "visual_update": visual_update,
            "truth_packet": truth,
            "next_actions": next_actions,
        }

    def _show_concept(
        self,
        command: str,
        mode: str,
        terms: tuple[str, ...],
        concept_name: str,
    ) -> dict[str, Any]:
        """Legacy keyword filter — searches only already-projected topology nodes.

        Preserved as a fallback for when the concept workspace engine is unavailable.
        In V1.1 all concept show commands go through _show_concept_workspace first.
        """
        lowered_terms = tuple(t.lower() for t in terms)
        highlighted = []
        for nid, node in self._node_by_id.items():
            search_text = " ".join(
                [
                    nid,
                    str(node.get("file_path", "")),
                    str(node.get("symbol", "")),
                    str(node.get("label", "")),
                ]
            ).lower()
            if any(term in search_text for term in lowered_terms):
                highlighted.append(nid)
        hidden = [nid for nid in self._all_node_ids if nid not in highlighted]
        self.state.active_filter = concept_name.lower().replace(" ", "_")
        self.state.visible_node_ids = highlighted
        self.state.hidden_node_ids = hidden
        self.state.add_event("filter", f"show {concept_name}: {len(highlighted)} nodes (legacy filter)")

        truth = _truth_packet_base()
        truth["files"] = sorted(
            {str(self._node_by_id[nid].get("file_path", "")) for nid in highlighted if nid in self._node_by_id}
        )
        truth["symbols"] = sorted(
            {str(self._node_by_id[nid].get("symbol", "")) for nid in highlighted if nid in self._node_by_id}
        )
        truth["line_ranges"] = [
            {
                "node_id": nid,
                "file_path": str(self._node_by_id[nid].get("file_path", "")),
                "symbol": str(self._node_by_id[nid].get("symbol", "")),
                "line_range": list(self._node_by_id[nid].get("line_range", [])),
            }
            for nid in highlighted
            if nid in self._node_by_id and self._node_by_id[nid].get("line_range")
        ]
        truth["grounding"] = "grounded" if highlighted else "NEEDS_GROUNDING"

        return {
            "ok": True,
            "answer": f"Highlighted {len(highlighted)} node(s) matching {concept_name}.",
            "visual_update": {
                "highlighted_node_ids": highlighted,
                "hidden_node_ids": hidden,
                "selected_node_ids": self.state.selected_node_ids,
                "ghost_edges": [ge for ge in self.state.ghost_edges],
                "labels": {nid: concept_name for nid in highlighted},
                "ui_hints": [f"{concept_name.lower().replace(' ', '_')}_filter_active"],
            },
            "truth_packet": truth,
            "next_actions": [
                "isolate selected",
                "diagnose selection",
                "show dependencies",
                "prepare agent task",
            ],
        }

    def _add_ghost_edge(self, source: str, target: str, *, note: str = "") -> dict[str, Any]:
        """Add a ghost edge to live state only. Never patch authority."""
        hypothesis_id = _short_hash(f"{source}->{target}:{note}:{time.time()}")
        ghost = GhostEdge(
            source=source,
            target=target,
            label="ghost_hypothesis",
            hypothesis_id=hypothesis_id,
            created_at=time.time(),
            note=note,
        )
        ghost_dict = ghost.to_dict()
        self.state.ghost_edges.append(ghost_dict)
        self.state.add_event("ghost_edge", f"{source} -> {target} ({hypothesis_id})")
        return ghost_dict

    def _find_test_nodes(self, selected: list[str]) -> list[str]:
        """Find test node IDs connected to the selection."""
        if not selected:
            # Return all test nodes.
            return [
                nid
                for nid, node in self._node_by_id.items()
                if str(node.get("node_type", "")) == "test"
                or str(node.get("file_path", "")).startswith(TEST_PREFIX)
            ]
        # Use micro-arena to find tests.
        try:
            micro = select_micro_arena(self.topology, selected, depth=1, human_instruction="show tests")
            tests = micro.get("tests", []) or []
            test_ids = []
            for test_file in tests:
                for nid, node in self._node_by_id.items():
                    if str(node.get("file_path", "")) == str(test_file):
                        test_ids.append(nid)
            return test_ids
        except Exception:  # noqa: BLE001
            return []

    def _find_test_files(self, selected: list[str]) -> list[str]:
        """Find test file paths connected to the selection."""
        if not selected:
            return []
        try:
            micro = select_micro_arena(self.topology, selected, depth=1, human_instruction="find tests")
            return list(micro.get("tests", []) or [])
        except Exception:  # noqa: BLE001
            return []

    def _selected_file_names(self, selected: list[str]) -> list[str]:
        """Return file paths for the selected nodes."""
        return [
            str(self._node_by_id.get(nid, {}).get("file_path", ""))
            for nid in selected
            if nid in self._node_by_id
        ]

    def _node_ids_for_files(self, files: Iterable[str]) -> list[str]:
        """Return node IDs whose file_path is in the given file list."""
        file_set = set(files)
        return [
            nid
            for nid, node in self._node_by_id.items()
            if str(node.get("file_path", "")) in file_set
        ]

    def _no_selection_result(self, cmd_name: str) -> dict[str, Any]:
        self.state.add_event("no_selection", cmd_name)
        return {
            "ok": True,
            "answer": f"No node selected for '{cmd_name}'. Select a node first.",
            "visual_update": _visual_update_base(),
            "truth_packet": _truth_packet_base_needs_grounding(),
            "next_actions": ["show ST3GG", "show JSpace", "show Agent Arena Bridge"],
        }

    def _error_result(self, command: str, error: str) -> dict[str, Any]:
        self.state.add_event("error", f"{command}: {error}")
        return {
            "ok": False,
            "answer": f"Command failed: {error}",
            "visual_update": _visual_update_base(),
            "truth_packet": _truth_packet_base_needs_grounding(),
            "next_actions": ["show ST3GG", "diagnose selection"],
        }


# ----------------------------------------------------------------------
# Module-level helpers
# ----------------------------------------------------------------------


def route_command(
    arena: HumanAgentArena,
    command: str,
    *,
    selected_node_ids: list[str] | None = None,
    mode: str = "explore",
) -> dict[str, Any]:
    """Convenience function to route a command through a HumanAgentArena instance."""
    return arena.route_command(command, selected_node_ids=selected_node_ids, mode=mode)


def _truth_packet_base() -> dict[str, Any]:
    """Base truth packet with invariant fields."""
    return {
        "files": [],
        "symbols": [],
        "line_ranges": [],
        "tests": [],
        "source_hashes": [],
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        "grounding": "NEEDS_GROUNDING",
    }


def _truth_packet_base_needs_grounding() -> dict[str, Any]:
    """Truth packet for cases where exact truth is missing."""
    tp = _truth_packet_base()
    tp["grounding"] = "NEEDS_GROUNDING"
    return tp


def _visual_update_base() -> dict[str, Any]:
    """Base visual update structure."""
    return {
        "highlighted_node_ids": [],
        "hidden_node_ids": [],
        "selected_node_ids": [],
        "ghost_edges": [],
        "labels": {},
        "ui_hints": [],
    }


def _truth_packet_from_micro(micro: dict[str, Any]) -> dict[str, Any]:
    """Build a truth packet from a micro-arena result."""
    truth = _truth_packet_base()
    nodes = micro.get("selected_nodes", []) or []
    truth["files"] = sorted({str(n.get("file_path", "")) for n in nodes if n.get("file_path")})
    truth["symbols"] = sorted({str(n.get("symbol", "")) for n in nodes if n.get("symbol")})
    truth["line_ranges"] = [
        {
            "node_id": str(n.get("id", "")),
            "file_path": str(n.get("file_path", "")),
            "symbol": str(n.get("symbol", "")),
            "line_range": list(n.get("line_range", [])),
        }
        for n in nodes
        if n.get("line_range")
    ]
    truth["tests"] = list(micro.get("tests", []) or [])
    truth["grounding"] = "grounded" if nodes else "NEEDS_GROUNDING"
    return truth


def _parse_depth(command: str, *, default: int = 2) -> int:
    """Parse 'depth N' from a command string."""
    import re

    match = re.search(r"depth\s+(\d+)", command, re.IGNORECASE)
    if match:
        return max(0, min(3, int(match.group(1))))
    return default


def _parse_what_if(command: str) -> tuple[str, str]:
    """Parse 'what if <source> connects to <target>'."""
    import re

    # "what if X connects to Y"
    match = re.search(
        r"what\s+if\s+(.+?)\s+connect(?:s)?\s+to\s+(.+)",
        command,
        re.IGNORECASE,
    )
    if match:
        return _resolve_node_ref(match.group(1).strip()), _resolve_node_ref(match.group(2).strip())
    # "what if connect source to target"
    match = re.search(
        r"what\s+if\s+connect\s+(.+?)\s+to\s+(.+)",
        command,
        re.IGNORECASE,
    )
    if match:
        return _resolve_node_ref(match.group(1).strip()), _resolve_node_ref(match.group(2).strip())
    return "", ""


def _parse_hypothesize(command: str) -> tuple[str, str]:
    """Parse 'hypothesize connection <source> <target>' or 'hypothesize connection from X to Y'."""
    import re

    match = re.search(
        r"hypothes(?:ize|is)\s+connection\s+(?:from\s+)?(.+?)\s+(?:to|->)\s+(.+)",
        command,
        re.IGNORECASE,
    )
    if match:
        return _resolve_node_ref(match.group(1).strip()), _resolve_node_ref(match.group(2).strip())
    return "", ""


def _resolve_node_ref(
    ref: str,
    *,
    existing_nodes: dict[str, dict[str, Any]] | None = None,
    workspace: Any | None = None,
) -> str:
    """Resolve a human-friendly node reference to a node ID if possible.

    Uses the concept workspace engine when available. Falls back to returning
    the ref as-is (stored as a ghost edge label) when unresolvable.
    """
    if _CONCEPTS_AVAILABLE and _resolve_node_ref_concepts is not None:
        result = _resolve_node_ref_concepts(ref, workspace=workspace, existing_nodes=existing_nodes)
        return str(result.get("resolved", ref))
    return str(ref or "").strip()


def _build_objective(
    command: str,
    selected: list[str],
    node_by_id: dict[str, dict[str, Any]],
) -> str:
    """Build a clear objective from the current command/selection."""
    parts: list[str] = []
    cmd_text = str(command or "").strip()
    if cmd_text and cmd_text.lower() != "prepare agent task":
        parts.append(cmd_text)
    if selected:
        for nid in selected[:3]:
            node = node_by_id.get(nid, {})
            file_path = str(node.get("file_path", ""))
            symbol = str(node.get("symbol", ""))
            if file_path and symbol:
                parts.append(f"Target: {file_path}::{symbol}")
            elif file_path:
                parts.append(f"Target: {file_path}")
    if not parts:
        return ""
    return " | ".join(parts)


def _short_hash(text: str, *, size: int = 12) -> str:
    return hashlib.blake2b(text.encode("utf-8", errors="replace"), digest_size=size).hexdigest()