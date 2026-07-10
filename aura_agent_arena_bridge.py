"""
Aura Agent Arena Bridge — Core bridge for external coding agents.

Exposes Aura's full Coding Arena pipeline (CODEMAP navigation, topology/symbol
lookup, micro-arena selection, action capsule compilation, context compression,
ST3GG egress, JSpace advisory state, FST/Coding Arena routing, Liquid Planning
Arena leases, boundary contracts, patch staging, verifier/test execution,
compressed repair packets, ledger/ICM export) to external agents without
requiring them to read the full repository.

Architectural rule:
  VSA, JSpace, ST3GG, screenshots, summaries, and fuzzy similarity are NOT the
  source of truth.  They may guide retrieval and reduce context, but exact
  source files, source spans, hashes, CODEMAP facts, tests, boundary contracts,
  and verifier gates are authority.
"""

from __future__ import annotations

import ast
import hashlib
import json
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from aura_agent_arena_errors import (
    ArenaBridgeError,
    error_from_shadow_finding,
    error_from_verification_failure,
    is_error_packet,
    make_error_packet,
)

_LOG = logging.getLogger(__name__)

BRIDGE_VERSION = "AURA_AGENT_ARENA_BRIDGE_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

# Files that are too large for direct reads — agents must use symbol search.
_BLOCKED_HUB_FILES = frozenset({
    "aura_node.py",
    "aura_live_architect.py",
    "aura_coding_arena_3d.py",
    "aura_music_coding_arena.py",
    "aura_emergent_result_verifier.py",
    "aura_empirical_software_lab.py",
    "aura_efficiency_benchmark.py",
})

DEFAULT_MAX_LINES = 120
DEFAULT_MAX_TOKENS_EST = 2000
DEFAULT_MAX_RESULTS = 10

_NAVIGATION_RULES = [
    "read CODEMAP first",
    "use symbol index before opening files",
    "open only top hits and neighbor files",
    "refresh touched paths incrementally",
]

_SOURCE_OF_TRUTH = [
    "CODEMAP.json",
    "understand_graph.json",
    "AST line ranges",
    "exact source files",
    "tests",
]

# Secret-like field names that must never appear in tool output.
_FORBIDDEN_OUTPUT_KEYS = frozenset({
    "raw_snapshot_bytes",
    "raw_sidecar_bytes",
    "raw_private_memory",
    "api_key",
    "secret",
    "password",
    "token",
    "private_key",
})


def _short_hash(text: str, *, size: int = 12) -> str:
    return hashlib.blake2b(text.encode("utf-8", errors="replace"), digest_size=size).hexdigest()


def _normalize_path(path: str | None) -> str | None:
    if path is None:
        return None
    normalized = str(path).replace("\\", "/").strip()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized or None


def _resolve_in_repo(file_path: str, repo_root: Path) -> Path | None:
    """Resolve *file_path* inside *repo_root*, rejecting absolute paths and escapes."""
    if not file_path:
        return None
    if os.path.isabs(file_path):
        return None
    normalized = _normalize_path(file_path)
    if not normalized:
        return None
    try:
        target = (repo_root / normalized).resolve()
        target.relative_to(repo_root.resolve())
        return target
    except (ValueError, OSError):
        return None


def _strip_secrets(obj: Any) -> Any:
    """Recursively remove secret-like keys from dicts/lists."""
    if isinstance(obj, dict):
        clean = {}
        for key, value in obj.items():
            key_lower = str(key).lower()
            if any(forbidden in key_lower for forbidden in _FORBIDDEN_OUTPUT_KEYS):
                continue
            clean[key] = _strip_secrets(value)
        return clean
    if isinstance(obj, list):
        return [_strip_secrets(item) for item in obj]
    return obj


def _estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // 4)


def _load_codemap(repo_root: Path) -> dict[str, Any] | None:
    codemap_path = repo_root / ".aura" / "CODEMAP.json"
    try:
        with codemap_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return None


def _find_symbol_line_range(file_path: Path, symbol_name: str) -> tuple[int, int] | None:
    """Use AST to find the line range of *symbol_name* in *file_path*."""
    try:
        source = file_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source)
    except (OSError, SyntaxError):
        return None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name == symbol_name:
                end_line = getattr(node, "end_lineno", node.lineno) or node.lineno
                return (node.lineno, end_line)
    return None


def _compress_text(raw: str, max_tokens: int) -> str:
    """Compress *raw* text if it exceeds *max_tokens* estimated tokens."""
    if _estimate_tokens(raw) <= max_tokens:
        return raw
    # Lazy import to avoid import chain issues at module load.
    try:
        from aura_context_crusher import AuraContextCrusher

        crusher = AuraContextCrusher()
        result = crusher.compress_context_stream(raw, source_hint="bridge_micro_context")
        return result.compressed_payload
    except Exception:  # noqa: BLE001
        # Fallback: truncate with marker.
        char_limit = max_tokens * 4
        return raw[:char_limit] + "\n...[compressed by bridge fallback]..."


class AuraAgentArenaBridge:
    """Core bridge exposing Aura's Coding Arena to external coding agents.

    All tool methods return a dict.  On failure, the dict is a structured
    error packet (see ``aura_agent_arena_errors``).
    """

    def __init__(self, *, repo_root: str | Path | None = None) -> None:
        if repo_root is None:
            try:
                from aura_substrate import REPO_ROOT as _REPO_ROOT

                self.repo_root = Path(_REPO_ROOT)
            except Exception:  # noqa: BLE001
                self.repo_root = Path.cwd()
        else:
            self.repo_root = Path(repo_root)
        self._sessions: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def _get_session(self, plan_phase_hash: str) -> dict[str, Any] | None:
        return self._sessions.get(plan_phase_hash)

    def _require_session(self, plan_phase_hash: str) -> dict[str, Any]:
        session = self._get_session(plan_phase_hash)
        if session is None:
            raise ArenaBridgeError(
                "missing_grounding",
                f"No prepared arena session for plan_phase_hash={plan_phase_hash}. "
                "Call aura_prepare_arena first.",
            )
        return session

    def _find_act_capsule(self, session: dict[str, Any], task_id: str) -> dict[str, Any] | None:
        arena = session.get("arena")
        if arena is None:
            return None
        for capsule in arena.agent_capsules:
            if str(capsule.get("task_id")) == str(task_id):
                return capsule
        return None

    def _find_grounding(self, session: dict[str, Any], task_id: str) -> dict[str, Any] | None:
        for evidence in session.get("grounding", []):
            if str(evidence.get("task_id")) == str(task_id):
                return evidence
        return None

    def _find_route_decision(self, session: dict[str, Any], task_id: str) -> dict[str, Any] | None:
        arena = session.get("arena")
        if arena is None:
            return None
        for decision in arena.routing_decisions:
            if str(decision.get("task_id")) == str(task_id):
                return decision
        return None

    # ------------------------------------------------------------------
    # Tool 1: aura_repo_digest
    # ------------------------------------------------------------------

    def aura_repo_digest(
        self,
        *,
        include_hubs: bool = True,
        max_lines: int = 120,
    ) -> dict[str, Any]:
        """Return a tiny, token-sparing repo orientation packet."""
        codemap = _load_codemap(self.repo_root)
        if codemap is None:
            return make_error_packet(
                "codemap_refresh_failed",
                "CODEMAP.json is missing or unreadable. Run CODEMAP generation first.",
                repair_hint="Generate .aura/CODEMAP.json before using the bridge.",
            )

        coverage = codemap.get("coverage", {})
        file_count = int(coverage.get("included_file_count", 0))
        all_paths = coverage.get("all_included_paths_sorted", []) or []
        if not file_count and all_paths:
            file_count = len(all_paths)

        symbol_index = codemap.get("symbol_index", {})
        topology = codemap.get("topology", {})
        topology_nodes = 0
        topology_edges = 0
        if isinstance(topology, dict):
            topology_nodes = len(topology.get("nodes", []) or [])
            topology_edges = len(topology.get("edges", []) or [])
        elif isinstance(topology, list):
            topology_nodes = len(topology)

        hubs = []
        if include_hubs:
            raw_hubs = codemap.get("hubs", []) or []
            for hub in raw_hubs[:12]:
                if isinstance(hub, dict):
                    hubs.append({
                        "path": str(hub.get("path", "")),
                        "role": str(hub.get("role", "")),
                        "symbols": int(hub.get("symbols", 0)),
                        "tokens_est": int(hub.get("tokens_est", 0)),
                        "topology_degree": int(hub.get("topology_degree", 0)),
                    })

        return {
            "version": BRIDGE_VERSION,
            "ok": True,
            "codemap_status": "AURA_CODEMAP_ACTIVE",
            "file_count": file_count,
            "topology_nodes": topology_nodes,
            "topology_edges": topology_edges,
            "symbol_count": len(symbol_index),
            "navigation_rules": list(_NAVIGATION_RULES),
            "hubs": hubs,
            "source_of_truth": list(_SOURCE_OF_TRUTH),
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    # ------------------------------------------------------------------
    # Tool 2: aura_prepare_arena
    # ------------------------------------------------------------------

    def aura_prepare_arena(
        self,
        *,
        objective: str,
        target_file: str | None = None,
        target_symbol: str | None = None,
        acceptance_criteria: list[str] | None = None,
        risk_map: list[str] | None = None,
        constraints: list[str] | None = None,
    ) -> dict[str, Any]:
        """Run Aura's own prepare pipeline for a coding task."""
        if not objective or not objective.strip():
            return make_error_packet(
                "mcp_protocol_error",
                "objective is required and must be non-empty.",
            )

        try:
            from aura_architect_loop import ArchitectFusionLoop
        except Exception as exc:  # noqa: BLE001
            return make_error_packet(
                "mcp_protocol_error",
                f"Cannot import ArchitectFusionLoop: {exc}",
            )

        # Build act tasks from the target file/symbol.
        act_task: dict[str, Any] = {"objective": objective}
        if target_file:
            act_task["target_file"] = _normalize_path(target_file)
        if target_symbol:
            act_task["target_symbol"] = target_symbol

        try:
            loop = ArchitectFusionLoop(repo_root=self.repo_root)
            prepared = loop.prepare(
                objective,
                architecture_decision=f"External agent bridge: {objective[:80]}",
                act_tasks=[act_task],
                target_file=_normalize_path(target_file),
                target_symbol=target_symbol,
                acceptance_criteria=acceptance_criteria,
                risk_map=risk_map,
                constraints=constraints,
            )
        except Exception as exc:  # noqa: BLE001
            return make_error_packet(
                "missing_grounding",
                f"Architect prepare pipeline failed: {exc}",
                repair_hint="Ensure CODEMAP.json exists and target file/symbol are valid.",
            )

        plan = prepared.plan
        arena = prepared.arena
        phase_hash = plan.phase_hash

        # Store session.
        self._sessions[phase_hash] = {
            "prepared": prepared,
            "arena": arena,
            "verification": None,
            "stage_results": [],
            "hotswap_capsule": None,
        }

        # Build compressed summary.
        act_summaries = [
            {
                "task_id": act.task_id,
                "target_file": act.target_file,
                "target_symbol": act.target_symbol,
                "size": act.size,
                "role": act.role,
                "objective": act.objective[:120],
            }
            for act in plan.act_capsules
        ]

        grounding_summary = [
            {
                "task_id": ev.task_id,
                "target_file": ev.target_file,
                "target_symbol": ev.target_symbol,
                "file_exists": ev.file_exists,
                "codemap_file_hit": ev.codemap_file_hit,
                "symbol_exists": ev.symbol_exists,
                "test_files": ev.test_files,
                "neighbor_files": ev.neighbor_files[:5],
            }
            for ev in prepared.grounding
        ]

        shadow_findings = [
            {
                "shadow_type": f.shadow_type,
                "severity": f.severity,
                "message": f.message,
                "task_id": f.task_id,
            }
            for f in prepared.shadow_report.findings
        ]

        routing_summary = [
            {
                "task_id": d.get("task_id"),
                "route": d.get("route"),
                "reason": d.get("reason"),
                "model": d.get("model"),
            }
            for d in arena.routing_decisions
        ]

        builder_authorized = bool(arena.routing_decisions) and all(
            d.get("route") == "BUILDER_PATCH" for d in arena.routing_decisions
        )

        blockers = [f for f in shadow_findings if f["severity"] == "blocker"]
        warnings = [f for f in shadow_findings if f["severity"] != "blocker"]

        return {
            "ok": True,
            "version": BRIDGE_VERSION,
            "plan_phase_hash": phase_hash,
            "act_capsules": act_summaries,
            "grounding_evidence": grounding_summary,
            "shadow_findings": shadow_findings,
            "shadow_gate": prepared.shadow_report.gate,
            "routing_decisions": routing_summary,
            "liquid_arena_lease_count": len(arena.agent_leases),
            "builder_patch_authorized": builder_authorized,
            "ready_for_incubator": arena.ready_for_incubator,
            "blockers": blockers,
            "warnings": warnings,
            "intensity": prepared.intensity,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    # ------------------------------------------------------------------
    # Tool 3: aura_get_micro_context
    # ------------------------------------------------------------------

    def aura_get_micro_context(
        self,
        *,
        plan_phase_hash: str,
        task_id: str,
        depth: int = 1,
        format: str = "both",
        max_tokens_est: int = DEFAULT_MAX_TOKENS_EST,
    ) -> dict[str, Any]:
        """Return the exact compressed context for one Act Capsule / selected topology node."""
        try:
            session = self._require_session(plan_phase_hash)
        except ArenaBridgeError as exc:
            return exc.to_packet()

        capsule = self._find_act_capsule(session, task_id)
        if capsule is None:
            return make_error_packet(
                "patch_outside_task",
                f"Task {task_id} not found in arena act capsules.",
                repair_hint="Use a task_id from aura_prepare_arena output.",
            )

        grounding = self._find_grounding(session, task_id)
        route_decision = self._find_route_decision(session, task_id)

        target_file = _normalize_path(capsule.get("target_file"))
        target_symbol = capsule.get("target_symbol")

        # Gather line ranges from grounding or AST.
        line_ranges: list[dict[str, Any]] = []
        if grounding:
            for hit in grounding.get("codemap_symbol_hits", []) or []:
                if isinstance(hit, dict):
                    line_ranges.append({
                        "file": hit.get("file", target_file),
                        "symbol": hit.get("name", target_symbol),
                        "line_range": [hit.get("line", 0), hit.get("end_line", 0)],
                    })

        # If no CODEMAP hits, try AST.
        if not line_ranges and target_file and target_symbol:
            resolved = _resolve_in_repo(target_file, self.repo_root)
            if resolved and resolved.exists():
                rng = _find_symbol_line_range(resolved, target_symbol)
                if rng:
                    line_ranges.append({
                        "file": target_file,
                        "symbol": target_symbol,
                        "line_range": [rng[0], rng[1]],
                    })

        # Gather dependencies, tests, neighbors from grounding.
        dependencies: list[str] = []
        tests: list[str] = []
        neighbors: list[str] = []
        if grounding:
            dependencies = list(grounding.get("neighbor_files", []) or [])[:10]
            tests = list(grounding.get("test_files", []) or [])
            neighbors = list(grounding.get("neighbor_files", []) or [])[:5]

        # Build compressed context string.
        context_parts: list[str] = []
        if target_file:
            context_parts.append(f"Target file: {target_file}")
        if target_symbol:
            context_parts.append(f"Target symbol: {target_symbol}")
        if line_ranges:
            context_parts.append(f"Line ranges: {json.dumps(line_ranges)}")
        if tests:
            context_parts.append(f"Tests: {', '.join(tests)}")
        if dependencies:
            context_parts.append(f"Dependencies: {', '.join(dependencies[:5])}")
        if route_decision:
            context_parts.append(f"Route: {route_decision.get('route')} ({route_decision.get('reason')})")

        raw_context = "\n".join(context_parts)
        compressed_context = _compress_text(raw_context, max_tokens_est)

        # Try to get JSpace packet and ST3GG egress from the arena.
        jspace_packet = ""
        st3gg_egress: dict[str, Any] = {}
        try:
            liquid_arena = session.get("arena").liquid_arena if session.get("arena") else {}
            if isinstance(liquid_arena, dict):
                jspace_packet = str(liquid_arena.get("jspace_packet", "") or "")
        except Exception:  # noqa: BLE001
            pass

        # Try compile_action_capsule if topology is available.
        capsule_context: dict[str, Any] = {}
        try:
            codemap = _load_codemap(self.repo_root)
            if codemap and target_file:
                topology = codemap.get("topology", {})
                if isinstance(topology, dict) and topology.get("nodes"):
                    from aura_coding_arena_3d import compile_action_capsule

                    # Find node IDs matching the target file.
                    nodes = topology.get("nodes", []) or []
                    selected_ids = [
                        n.get("id", "")
                        for n in nodes
                        if isinstance(n, dict) and _normalize_path(n.get("file_path", "")) == target_file
                    ][:5]
                    if selected_ids:
                        compiled = compile_action_capsule(
                            topology,
                            selected_ids,
                            human_instruction=capsule.get("objective", ""),
                            depth=depth,
                        )
                        capsule_context = {
                            "target_files": compiled.get("context", {}).get("target_files", []),
                            "target_symbols": compiled.get("context", {}).get("target_symbols", []),
                            "line_ranges": compiled.get("context", {}).get("line_ranges", []),
                            "dependencies": compiled.get("context", {}).get("dependencies", []),
                            "tests": compiled.get("context", {}).get("tests", []),
                            "neighbors": compiled.get("context", {}).get("neighbors", [])[:5],
                        }
                        if compiled.get("route_decision"):
                            route_decision = compiled["route_decision"]
                        if compiled.get("jspace_packet"):
                            jspace_packet = str(compiled["jspace_packet"])
                        if compiled.get("st3gg_egress"):
                            st3gg_egress = compiled["st3gg_egress"]
        except Exception:  # noqa: BLE001
            pass

        # Merge capsule_context if we got it.
        if capsule_context:
            if capsule_context.get("line_ranges") and not line_ranges:
                line_ranges = capsule_context["line_ranges"]
            if capsule_context.get("dependencies") and not dependencies:
                dependencies = capsule_context["dependencies"]
            if capsule_context.get("tests") and not tests:
                tests = capsule_context["tests"]

        result = {
            "ok": True,
            "task_id": task_id,
            "target_file": target_file,
            "target_symbol": target_symbol,
            "line_ranges": line_ranges,
            "dependencies": dependencies[:10],
            "tests": tests,
            "route_decision": route_decision or {},
            "jspace_packet": jspace_packet[:500] if jspace_packet else "",
            "st3gg_egress": st3gg_egress,
            "compressed_context": compressed_context,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        return _strip_secrets(result)

    # ------------------------------------------------------------------
    # Tool 4: aura_search_code
    # ------------------------------------------------------------------

    def aura_search_code(
        self,
        *,
        query: str,
        search_kind: str = "symbol",
        max_results: int = DEFAULT_MAX_RESULTS,
        include_neighbors: bool = True,
    ) -> dict[str, Any]:
        """Search through Aura's CODEMAP without dumping files."""
        if not query or not query.strip():
            return make_error_packet("mcp_protocol_error", "query is required.")

        codemap = _load_codemap(self.repo_root)
        if codemap is None:
            return make_error_packet(
                "codemap_refresh_failed",
                "CODEMAP.json is missing. Cannot search.",
            )

        results: list[dict[str, Any]] = []
        query_lower = query.strip().lower()

        if search_kind == "symbol":
            symbol_index = codemap.get("symbol_index", {})
            # Exact match first.
            hits = symbol_index.get(query, [])
            if not hits:
                # Fuzzy: prefix/substring match on symbol names.
                for name, symbol_hits in symbol_index.items():
                    if query_lower in name.lower():
                        hits = symbol_hits
                        break
            for hit in hits[:max_results]:
                if isinstance(hit, dict):
                    file_path = _normalize_path(hit.get("file", ""))
                    neighbors: list[str] = []
                    if include_neighbors and file_path:
                        # Find neighbor files from topology.
                        topology = codemap.get("topology", {})
                        if isinstance(topology, dict):
                            for node in topology.get("nodes", []) or []:
                                if isinstance(node, dict) and _normalize_path(node.get("file_path")) == file_path:
                                    neighbors = [
                                        _normalize_path(e.get("file_path", ""))
                                        for e in (topology.get("nodes", []) or [])
                                        if isinstance(e, dict)
                                        and _normalize_path(e.get("file_path")) != file_path
                                        and e.get("id") in (node.get("dependencies", []) or [])
                                    ][:3]
                                    break
                    results.append({
                        "file": file_path or "",
                        "symbol": str(hit.get("name", query)),
                        "line_range": [int(hit.get("line", 0)), int(hit.get("end_line", 0))],
                        "reason": "symbol hit",
                        "neighbors": neighbors,
                    })

        elif search_kind == "file":
            files = codemap.get("files", {})
            if isinstance(files, dict):
                for path_key in files:
                    if query_lower in str(path_key).lower():
                        results.append({
                            "file": str(path_key),
                            "symbol": "",
                            "line_range": [],
                            "reason": "file hit",
                            "neighbors": [],
                        })
                        if len(results) >= max_results:
                            break
            elif isinstance(files, list):
                for item in files:
                    path_str = str(item.get("path", item) if isinstance(item, dict) else item)
                    if query_lower in path_str.lower():
                        results.append({
                            "file": path_str,
                            "symbol": "",
                            "line_range": [],
                            "reason": "file hit",
                            "neighbors": [],
                        })
                        if len(results) >= max_results:
                            break

        elif search_kind == "text":
            # Fallback: grep through files.
            results = self._grep_search(query, max_results, include_neighbors)

        elif search_kind == "command":
            command_index = codemap.get("command_index", {})
            if isinstance(command_index, dict):
                for cmd, info in command_index.items():
                    if query_lower in str(cmd).lower():
                        if isinstance(info, dict):
                            results.append({
                                "file": str(info.get("file", "")),
                                "symbol": str(info.get("symbol", cmd)),
                                "line_range": [int(info.get("line", 0)), int(info.get("end_line", 0))],
                                "reason": "command hit",
                                "neighbors": [],
                            })
                        if len(results) >= max_results:
                            break

        if not results:
            # Final fallback: grep.
            results = self._grep_search(query, max_results, include_neighbors)

        return {
            "ok": True,
            "results": results[:max_results],
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def _grep_search(self, query: str, max_results: int, include_neighbors: bool) -> list[dict[str, Any]]:
        """Fallback text search using grep."""
        results: list[dict[str, Any]] = []
        try:
            cmd = [
                "grep", "-rn", "--include=*.py", "-l",
                query,
                str(self.repo_root),
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            for line in proc.stdout.strip().splitlines()[:max_results]:
                rel = line.replace(str(self.repo_root) + "/", "").strip()
                results.append({
                    "file": rel,
                    "symbol": "",
                    "line_range": [],
                    "reason": "text hit",
                    "neighbors": [],
                })
        except Exception:  # noqa: BLE001
            pass
        return results

    # ------------------------------------------------------------------
    # Tool 5: aura_read_slice
    # ------------------------------------------------------------------

    def aura_read_slice(
        self,
        *,
        file: str,
        symbol: str | None = None,
        line_start: int | None = None,
        line_end: int | None = None,
        max_lines: int = DEFAULT_MAX_LINES,
    ) -> dict[str, Any]:
        """Read only authorized slices from source files."""
        normalized = _normalize_path(file)
        if not normalized:
            return make_error_packet("mcp_protocol_error", "file is required.")

        # Block hub files by default.
        file_name = Path(normalized).name
        if file_name in _BLOCKED_HUB_FILES and line_start is None and symbol is None:
            return make_error_packet(
                "scope_too_broad",
                f"File '{file_name}' is a large hub file. Use aura_search_code with search_kind=symbol instead.",
                repair_hint=f"Search for symbols in {file_name} using aura_search_code, then read specific symbol slices.",
                next_allowed_tools=["aura_search_code", "aura_get_micro_context"],
            )

        # Reject absolute paths.
        if os.path.isabs(file):
            return make_error_packet(
                "patch_outside_arena",
                "Absolute paths are not allowed. Use repo-relative paths.",
            )

        resolved = _resolve_in_repo(normalized, self.repo_root)
        if resolved is None or not resolved.exists():
            return make_error_packet(
                "missing_grounding",
                f"File '{normalized}' does not exist or resolves outside repo root.",
            )

        # Determine line range.
        if symbol:
            rng = _find_symbol_line_range(resolved, symbol)
            if rng is None:
                return make_error_packet(
                    "target_symbol_unresolved",
                    f"Symbol '{symbol}' not found in {normalized}.",
                    repair_hint="Use aura_search_code to find the correct symbol name.",
                )
            line_start = rng[0]
            line_end = rng[1]
        elif line_start is None:
            line_start = 1
        if line_end is None:
            line_end = line_start + max_lines - 1

        # Enforce max_lines.
        if line_end - line_start + 1 > max_lines:
            line_end = line_start + max_lines - 1

        try:
            all_lines = resolved.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError as exc:
            return make_error_packet("missing_grounding", f"Cannot read file: {exc}")

        total_lines = len(all_lines)
        start_idx = max(0, line_start - 1)
        end_idx = min(total_lines, line_end)
        slice_lines = all_lines[start_idx:end_idx]
        raw_content = "\n".join(slice_lines)

        # Sanitize through tokenizer guard.
        try:
            from aura_tokenizer_guard import sanitize_tokenizer_channels

            guard = sanitize_tokenizer_channels(raw_content)
            safe_content = guard.sanitized_text
            warnings = guard.warnings()
        except Exception:  # noqa: BLE001
            safe_content = raw_content
            warnings = []

        # Compress if over threshold.
        compressed = _compress_text(safe_content, max_tokens=max_lines * 4)

        return {
            "ok": True,
            "file": normalized,
            "symbol": symbol or "",
            "line_start": line_start,
            "line_end": end_idx,
            "total_lines": total_lines,
            "content": compressed,
            "warnings": list(warnings) if warnings else [],
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    # ------------------------------------------------------------------
    # Tool 6: aura_stage_patch
    # ------------------------------------------------------------------

    def aura_stage_patch(
        self,
        *,
        plan_phase_hash: str,
        task_id: str,
        owner: str = "external_agent",
        diff: str,
        affected_files: list[str],
        affected_symbols: list[str] | None = None,
        tests: list[str] | None = None,
    ) -> dict[str, Any]:
        """Stage a patch through Aura's Refactor Arena boundary logic."""
        try:
            session = self._require_session(plan_phase_hash)
        except ArenaBridgeError as exc:
            return exc.to_packet()

        arena = session["arena"]

        # Validate diff is non-empty.
        if not str(diff or "").strip():
            return make_error_packet(
                "empty_patch",
                "Patch submission has no diff body.",
                repair_hint="Provide a unified diff with file headers.",
            )

        try:
            from aura_architect_loop import stage_arena_patch

            result = stage_arena_patch(
                arena,
                task_id=task_id,
                owner=owner,
                diff=diff,
                affected_files=affected_files,
                affected_symbols=affected_symbols,
                tests=tests,
            )
        except Exception as exc:  # noqa: BLE001
            return make_error_packet(
                "mcp_protocol_error",
                f"stage_arena_patch raised: {exc}",
            )

        if not result.ok:
            # Convert findings to error packets.
            findings = [f.to_dict() if hasattr(f, "to_dict") else f for f in result.findings]
            first_finding = findings[0] if findings else {}
            err = error_from_shadow_finding(first_finding)
            return {
                **err.to_packet(),
                "findings": findings,
                "task_id": task_id,
            }

        # Store stage result.
        session["stage_results"].append(result)

        patch_summary = {
            "patch_id": result.patch.patch_id if result.patch else "",
            "task_id": task_id,
            "owner": owner,
            "affected_files": result.patch.affected_files if result.patch else [],
            "status": result.patch.status if result.patch else "rejected",
        }

        return {
            "ok": True,
            "patch": patch_summary,
            "arena_affected_files": list(arena.affected_files),
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    # ------------------------------------------------------------------
    # Tool 7: aura_verify_arena
    # ------------------------------------------------------------------

    def aura_verify_arena(
        self,
        *,
        plan_phase_hash: str,
        test_scope: str = "focused",
        runner: str = "pytest",
        max_log_lines: int = 80,
    ) -> dict[str, Any]:
        """Run verifiers/tests and return compressed machine-readable result."""
        try:
            session = self._require_session(plan_phase_hash)
        except ArenaBridgeError as exc:
            return exc.to_packet()

        arena = session["arena"]

        # Build test runner callback.
        test_runner = self._build_test_runner(runner, test_scope, session)

        try:
            from aura_architect_loop import verify_refactor_arena

            verification = verify_refactor_arena(
                arena,
                repo_root=self.repo_root,
                runner=test_runner,
            )
        except Exception as exc:  # noqa: BLE001
            return make_error_packet(
                "test_failed",
                f"verify_refactor_arena raised: {exc}",
            )

        session["verification"] = verification

        # Compress log.
        log_lines: list[str] = []
        for check in verification.checks:
            log_lines.append(f"[{check.get('stage')}] {check.get('status')}: {check.get('message', '')}")
        raw_log = "\n".join(log_lines)
        compressed_log = _compress_text(raw_log, max_tokens=max_log_lines * 4)

        # Determine next action.
        if verification.hotswap_ready:
            next_action = "promote_hotswap"
        elif any(f.get("stage") in {"patch_boundary", "patch_task_boundary", "patch_conflict"} for f in verification.failures):
            next_action = "escalate_to_judge"
        elif any(f.get("stage") == "tests" for f in verification.failures):
            next_action = "repair_with_builder"
        elif any(f.get("stage") == "patch_queue" for f in verification.failures):
            next_action = "wait_for_builder"
        else:
            next_action = "escalate_to_judge"

        # Try CODEMAP refresh for touched files.
        try:
            from aura_codebase_navigator import refresh_codemap_for_paths

            refresh_codemap_for_paths(
                list(arena.affected_files),
                root=self.repo_root,
                include_topology=True,
            )
        except Exception:  # noqa: BLE001
            pass

        return {
            "ok": verification.ok,
            "stage": verification.stage,
            "checks": verification.checks[:20],
            "failures": verification.failures[:10],
            "compressed_log": compressed_log,
            "next_action": next_action,
            "hotswap_ready": verification.hotswap_ready,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def _build_test_runner(self, runner: str, test_scope: str, session: dict[str, Any]) -> Any:
        """Build a test runner callback for verify_refactor_arena."""

        def run_test(test_name: str) -> dict[str, Any]:
            if runner != "pytest":
                return {"status": "skipped", "reason": f"runner {runner} not supported"}
            # Resolve test path.
            test_path = _normalize_path(test_name)
            if not test_path:
                return {"status": "failed", "reason": "invalid test path"}
            resolved = _resolve_in_repo(test_path, self.repo_root)
            if resolved is None or not resolved.exists():
                return {"status": "failed", "reason": f"test file not found: {test_path}"}
            try:
                cmd = [
                    "python", "-m", "pytest",
                    str(resolved),
                    "-q", "--tb=short", "--no-header",
                ]
                if test_scope == "focused":
                    cmd.extend(["-x", "--lf"])
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                return {
                    "status": "passed" if proc.returncode == 0 else "failed",
                    "returncode": proc.returncode,
                    "stdout": proc.stdout[:2000],
                    "stderr": proc.stderr[:1000],
                }
            except subprocess.TimeoutExpired:
                return {"status": "failed", "reason": "test timed out"}
            except Exception as exc:  # noqa: BLE001
                return {"status": "failed", "reason": str(exc)}

        return run_test

    # ------------------------------------------------------------------
    # Tool 8: aura_repair_packet
    # ------------------------------------------------------------------

    def aura_repair_packet(
        self,
        *,
        plan_phase_hash: str,
        task_id: str,
        failure_id: str | None = None,
        max_tokens_est: int = 1500,
    ) -> dict[str, Any]:
        """Return the minimum context needed for the agent to repair a failed patch."""
        try:
            session = self._require_session(plan_phase_hash)
        except ArenaBridgeError as exc:
            return exc.to_packet()

        verification = session.get("verification")
        if verification is None:
            return make_error_packet(
                "test_failed",
                "No verification result found. Call aura_verify_arena first.",
            )

        # Find the first relevant failure.
        failures = verification.failures
        if failure_id:
            failures = [f for f in failures if f.get("stage") == failure_id]
        if not failures:
            failures = verification.failures

        if not failures:
            return {
                "ok": True,
                "task_id": task_id,
                "failed_check": "",
                "compressed_error": "No failures found. Arena is ready for hotswap.",
                "allowed_files": [],
                "line_ranges": [],
                "original_patch_summary": "",
                "do_not_touch": [],
                "required_response": "unified diff only",
                "patch_authority": PATCH_AUTHORITY,
                "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            }

        failure = failures[0]
        err = error_from_verification_failure(failure)

        # Get allowed files from arena.
        arena = session["arena"]
        capsule = self._find_act_capsule(session, task_id)
        allowed_files: list[str] = []
        do_not_touch: list[str] = []
        if capsule:
            target_file = _normalize_path(capsule.get("target_file"))
            if target_file:
                allowed_files.append(target_file)
            for rf in capsule.get("related_files", []) or []:
                normalized = _normalize_path(rf)
                if normalized:
                    allowed_files.append(normalized)
        # Files in arena but not in this task's scope are do-not-touch.
        for af in arena.affected_files:
            if af not in allowed_files:
                do_not_touch.append(af)

        # Get line ranges from grounding.
        line_ranges: list[dict[str, Any]] = []
        grounding = self._find_grounding(session, task_id)
        if grounding:
            for hit in grounding.get("codemap_symbol_hits", []) or []:
                if isinstance(hit, dict):
                    line_ranges.append({
                        "file": hit.get("file", ""),
                        "symbol": hit.get("name", ""),
                        "line_range": [hit.get("line", 0), hit.get("end_line", 0)],
                    })

        # Original patch summary.
        original_patch_summary = ""
        for sr in session.get("stage_results", []):
            if sr.patch and sr.patch.task_id == task_id:
                original_patch_summary = f"patch_id={sr.patch.patch_id}, files={sr.patch.affected_files}"
                break

        # Compress error.
        compressed_error = _compress_text(
            f"{failure.get('stage')}: {failure.get('message', '')}\n{json.dumps(failure, default=str)}",
            max_tokens=max_tokens_est,
        )

        return {
            "ok": True,
            "task_id": task_id,
            "failed_check": failure.get("stage", ""),
            "compressed_error": compressed_error,
            "allowed_files": allowed_files,
            "line_ranges": line_ranges[:5],
            "original_patch_summary": original_patch_summary,
            "do_not_touch": do_not_touch,
            "required_response": "unified diff only",
            "error_category": err.category,
            "repair_hint": err.repair_hint,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    # ------------------------------------------------------------------
    # Tool 9: aura_hotswap_status
    # ------------------------------------------------------------------

    def aura_hotswap_status(
        self,
        *,
        plan_phase_hash: str,
    ) -> dict[str, Any]:
        """Return whether the staged transaction is ready for promotion/human review."""
        try:
            session = self._require_session(plan_phase_hash)
        except ArenaBridgeError as exc:
            return exc.to_packet()

        arena = session["arena"]
        verification = session.get("verification")

        if verification is None:
            return make_error_packet(
                "test_failed",
                "No verification result found. Call aura_verify_arena first.",
            )

        try:
            from aura_architect_loop import (
                build_hotswap_capsule,
                build_rollback_capsule,
                judge_refactor_arena,
            )

            judge = judge_refactor_arena(verification)
            hotswap = build_hotswap_capsule(arena, verification, repo_root=self.repo_root)
            rollback = build_rollback_capsule(arena, repo_root=self.repo_root)
        except Exception as exc:  # noqa: BLE001
            return make_error_packet(
                "mcp_protocol_error",
                f"Hotswap/rollback build failed: {exc}",
            )

        session["hotswap_capsule"] = hotswap

        return {
            "ok": True,
            "status": hotswap.get("status", "blocked"),
            "judge_decision": judge.get("decision", ""),
            "judge_next_gate": judge.get("next_gate", ""),
            "rollback_capsule": {
                "phase_hash": rollback.get("phase_hash", ""),
                "files": rollback.get("files", [])[:10],
                "rollback_hint": rollback.get("rollback_hint", ""),
            },
            "human_review_required": True,
            "hotswap_phase_hash": hotswap.get("phase_hash", ""),
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    # ------------------------------------------------------------------
    # Tool 10: aura_export_icm
    # ------------------------------------------------------------------

    def aura_export_icm(
        self,
        *,
        plan_phase_hash: str,
        workspace_root: str | None = None,
    ) -> dict[str, Any]:
        """Export the current arena transaction into ICM audit workspace."""
        try:
            session = self._require_session(plan_phase_hash)
        except ArenaBridgeError as exc:
            return exc.to_packet()

        arena = session["arena"]

        # Determine workspace root.
        ws_root = workspace_root or "Aura_Memory/icm_workspaces"
        if os.path.isabs(ws_root):
            return make_error_packet(
                "patch_outside_arena",
                "workspace_root must be relative; absolute paths are not allowed.",
            )

        # Build a LiquidPlanningArena-like object for export_arena_to_icm.
        try:
            from aura_liquid_planning_arena import LiquidPlanningArena, export_arena_to_icm

            # Reconstruct a LiquidPlanningArena from the arena transaction.
            liquid_data = arena.liquid_arena if isinstance(arena.liquid_arena, dict) else {}
            liquid_arena = LiquidPlanningArena(
                arena_version=liquid_data.get("arena_version", ""),
                arena_id=liquid_data.get("arena_id", ""),
                domain=liquid_data.get("domain", "code"),
                intent=liquid_data.get("intent", ""),
                plan_ref=liquid_data.get("plan_ref", ""),
                domain_objects=liquid_data.get("domain_objects", []),
                action_capsules=liquid_data.get("action_capsules", []),
                boundary_contracts=liquid_data.get("boundary_contracts", []),
                agent_leases=liquid_data.get("agent_leases", []),
                shared_action_queue=liquid_data.get("shared_action_queue", []),
                verification_ledger=liquid_data.get("verification_ledger", []),
                adapter=liquid_data.get("adapter", {}),
                phase_hash=liquid_data.get("phase_hash", ""),
            )

            resolved_ws = (self.repo_root / ws_root).resolve()
            ref = export_arena_to_icm(liquid_arena, str(resolved_ws))
        except Exception as exc:  # noqa: BLE001
            # Fallback: use the simpler ICM export.
            try:
                from aura_icm_workspace import export_arena_transaction

                txn = {
                    "objective": arena.liquid_arena.get("intent", "") if isinstance(arena.liquid_arena, dict) else "",
                    "domain": "code",
                    "arena_id": arena.liquid_arena.get("arena_id", "") if isinstance(arena.liquid_arena, dict) else "",
                    "arena_version": arena.arena_version,
                    "phase_hash": arena.plan_phase_hash,
                }
                resolved_ws = (self.repo_root / ws_root).resolve()
                ref = export_arena_transaction(
                    txn,
                    str(resolved_ws),
                    domain="code",
                    arena_id=txn["arena_id"],
                    arena_version=txn["arena_version"],
                )
            except Exception as exc2:  # noqa: BLE001
                return make_error_packet(
                    "mcp_protocol_error",
                    f"ICM export failed: {exc}; fallback also failed: {exc2}",
                )

        ref_dict = {}
        if hasattr(ref, "to_dict"):
            ref_dict = ref.to_dict()
        elif isinstance(ref, dict):
            ref_dict = ref
        else:
            ref_dict = {
                "workspace_path": getattr(ref, "workspace_path", str(resolved_ws)),
                "txn_id": getattr(ref, "txn_id", ""),
                "domain": getattr(ref, "domain", "code"),
                "arena_id": getattr(ref, "arena_id", ""),
            }

        return {
            "ok": True,
            "workspace_path": ref_dict.get("workspace_path", str(resolved_ws)),
            "txn_id": ref_dict.get("txn_id", ""),
            "domain": ref_dict.get("domain", "code"),
            "arena_id": ref_dict.get("arena_id", ""),
            "status": "exported_audit_layer_only",
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    # ------------------------------------------------------------------
    # Tool 11: aura_find_affordances (Intelligence Layer)
    # ------------------------------------------------------------------

    def aura_find_affordances(
        self,
        *,
        objective: str,
        target_files: list[str] | None = None,
        target_symbols: list[str] | None = None,
        include_affordances: bool = True,
        top_k: int = 7,
    ) -> dict[str, Any]:
        """Expose the Aura Affordance Directory to external coding agents.

        Tells agents which internal Aura tools should be considered before
        inventing generic solutions. Returns top 3–7 affordance cards only.
        Affordance cards are advisory — never patch authority.
        """
        if not objective or not objective.strip():
            return make_error_packet(
                "mcp_protocol_error",
                "objective is required and must be non-empty.",
            )

        try:
            from aura_affordance_directory import find_affordances

            result = find_affordances(
                objective=objective,
                target_files=target_files,
                target_symbols=target_symbols,
                repo_root=self.repo_root,
                top_k=min(max(top_k, 3), 7) if include_affordances else 0,
            )
        except Exception as exc:  # noqa: BLE001
            return make_error_packet(
                "missing_grounding",
                f"Affordance directory lookup failed: {exc}",
                repair_hint="Ensure aura_affordance_directory.py is importable.",
            )

        return {
            "ok": True,
            "version": BRIDGE_VERSION,
            "objective": objective,
            "recommended_affordances": result.get("recommended_affordances", []),
            "prompt_cards": result.get("prompt_cards", []),
            "do_not_reinvent": result.get("do_not_reinvent", []),
            "route_frame": result.get("route_frame", {}),
            "grounding": result.get("grounding", "NEEDS_GROUNDING"),
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            "note": (
                "These are advisory affordance cards. They tell you which internal "
                "Aura tools to consider. They are NOT patch authority. "
                "Patch authority remains exact source spans and hashes only."
            ),
        }

    # ------------------------------------------------------------------
    # Utility: list all available tools
    # ------------------------------------------------------------------

    @staticmethod
    def list_tools() -> list[dict[str, Any]]:
        """Return the list of all bridge tools and their descriptions."""
        return [
            {
                "name": "aura_repo_digest",
                "description": "Return a tiny, token-sparing repo orientation packet.",
                "required_inputs": [],
            },
            {
                "name": "aura_prepare_arena",
                "description": "Run Aura's own prepare pipeline for a coding task.",
                "required_inputs": ["objective"],
            },
            {
                "name": "aura_get_micro_context",
                "description": "Return the exact compressed context for one Act Capsule.",
                "required_inputs": ["plan_phase_hash", "task_id"],
            },
            {
                "name": "aura_search_code",
                "description": "Search through Aura's CODEMAP without dumping files.",
                "required_inputs": ["query"],
            },
            {
                "name": "aura_read_slice",
                "description": "Read only authorized slices from source files.",
                "required_inputs": ["file"],
            },
            {
                "name": "aura_stage_patch",
                "description": "Stage a patch through Aura's Refactor Arena boundary logic.",
                "required_inputs": ["plan_phase_hash", "task_id", "diff", "affected_files"],
            },
            {
                "name": "aura_verify_arena",
                "description": "Run verifiers/tests and return compressed machine-readable result.",
                "required_inputs": ["plan_phase_hash"],
            },
            {
                "name": "aura_repair_packet",
                "description": "Return the minimum context needed to repair a failed patch.",
                "required_inputs": ["plan_phase_hash", "task_id"],
            },
            {
                "name": "aura_hotswap_status",
                "description": "Return whether the staged transaction is ready for promotion.",
                "required_inputs": ["plan_phase_hash"],
            },
            {
                "name": "aura_export_icm",
                "description": "Export the current arena transaction into ICM audit workspace.",
                "required_inputs": ["plan_phase_hash"],
            },
            {
                "name": "aura_fireworks_patch_worker",
                "description": "Call a Fireworks model for a compressed micro-patch (candidate diff only).",
                "required_inputs": ["task_id", "compressed_context", "instruction"],
            },
            {
                "name": "aura_find_affordances",
                "description": "Find internal Aura tools to consider before inventing generic solutions. Returns top 3-7 advisory affordance cards.",
                "required_inputs": ["objective"],
            },
        ]