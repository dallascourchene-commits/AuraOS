"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9f5-[Q-SYS:NODE_INSPECTOR]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Node Intelligence & Lazy Expansion)
DEPENDENCIES: __future__, dataclasses, hashlib, json, pathlib, re, typing
FUNCTIONS: NodeIntelligencePacket, inspect_node, expand_node, route_node_command,
           why_is_node_here
SYNOPSIS: Node Intelligence layer for the Human Agent Arena. Produces grounded
NodeIntelligencePackets for any node — exact topology or CODEMAP-projected.
Supports lazy expansion (children, callers, callees, tests, docs, risks, full, balanced).
Uses FST/JSpace route frames for command routing. JSpace/FST remain advisory only.
No production code is mutated. No network calls. No heavy dependencies.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import re
import time
from typing import Any

NODE_INSPECTOR_VERSION = "AURA_NODE_INSPECTOR_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

# ---------------------------------------------------------------------------
# Node origin constants (grounded node ontology)
# ---------------------------------------------------------------------------

ORIGIN_EXACT_TOPOLOGY = "exact_topology_node"
ORIGIN_CODEMAP_PROJECTED = "codemap_projected_node"
ORIGIN_INFERRED_EDGE = "inferred_relationship_edge"
ORIGIN_GHOST_HYPOTHESIS = "ghost_hypothesis_edge"
ORIGIN_UNRESOLVED = "unresolved_candidate"

# ---------------------------------------------------------------------------
# NodeIntelligencePacket dataclass
# ---------------------------------------------------------------------------


@dataclass
class NodeIntelligencePacket:
    """Grounded intelligence packet for a single node."""

    node_id: str = ""
    node_origin: str = ORIGIN_UNRESOLVED
    why_here: str = ""
    grounding_source: str = ""
    file_path: str = ""
    symbol: str = ""
    kind: str = ""
    line_range: list[int] = field(default_factory=list)
    digest8: str = ""
    semantic_id: str = ""
    signature_hash: str = ""
    entity_exists: bool = False
    patch_authority: bool = False
    vsa_patch_authority: bool = False
    relationships: dict[str, list[str]] = field(default_factory=dict)
    risk: dict[str, Any] = field(default_factory=dict)
    jspace_state: dict[str, Any] = field(default_factory=dict)
    fst_route: dict[str, Any] = field(default_factory=dict)
    recommended_affordances: list[dict[str, Any]] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    confidence: float = 0.0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_origin": self.node_origin,
            "why_here": self.why_here,
            "grounding_source": self.grounding_source,
            "file_path": self.file_path,
            "symbol": self.symbol,
            "kind": self.kind,
            "line_range": list(self.line_range),
            "digest8": self.digest8,
            "semantic_id": self.semantic_id,
            "signature_hash": self.signature_hash,
            "entity_exists": self.entity_exists,
            "patch_authority": self.patch_authority,
            "vsa_patch_authority": self.vsa_patch_authority,
            "relationships": dict(self.relationships),
            "risk": dict(self.risk),
            "jspace_state": dict(self.jspace_state),
            "fst_route": dict(self.fst_route),
            "recommended_affordances": list(self.recommended_affordances),
            "next_actions": list(self.next_actions),
            "confidence": self.confidence,
            "notes": list(self.notes),
            "patch_authority_policy": PATCH_AUTHORITY,
            "vsa_patch_authority_policy": VSA_PATCH_AUTHORITY,
        }

    def to_truth_packet(self) -> dict[str, Any]:
        return {
            "files": [self.file_path] if self.file_path else [],
            "symbols": [self.symbol] if self.symbol else [],
            "line_ranges": [{
                "node_id": self.node_id,
                "file_path": self.file_path,
                "symbol": self.symbol,
                "line_range": list(self.line_range),
            }] if self.line_range else [],
            "source_hashes": [self.digest8] if self.digest8 else [],
            "signature_hashes": [self.signature_hash] if self.signature_hash else [],
            "node_origins": {self.node_id: self.node_origin},
            "codemap_projected_nodes": [self.node_id] if self.node_origin == ORIGIN_CODEMAP_PROJECTED else [],
            "exact_topology_nodes": [self.node_id] if self.node_origin == ORIGIN_EXACT_TOPOLOGY else [],
            "ghost_hypothesis_edges": [],
            "unresolved_candidates": [self.node_id] if self.node_origin == ORIGIN_UNRESOLVED else [],
            "grounding_source": self.grounding_source or ".aura/CODEMAP.json",
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            "grounding": "grounded" if self.entity_exists else "NEEDS_GROUNDING",
        }


# ---------------------------------------------------------------------------
# CODEMAP loader (read-only, cached — mirrors concepts.py)
# ---------------------------------------------------------------------------

_CODEMAP_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_CODEMAP_TTL = 120.0


def _load_codemap(repo_root: Path) -> dict[str, Any]:
    path = repo_root / ".aura" / "CODEMAP.json"
    key = str(path)
    now = time.time()
    if key in _CODEMAP_CACHE:
        ts, data = _CODEMAP_CACHE[key]
        if now - ts < _CODEMAP_TTL:
            return data
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        _CODEMAP_CACHE[key] = (now, data)
        return data
    except Exception:
        return {}


def _short_hash(text: str, *, size: int = 8) -> str:
    return hashlib.blake2b(text.encode("utf-8", errors="replace"), digest_size=size).hexdigest()


def _stable_node_id(file_path: str, symbol: str = "") -> str:
    if symbol:
        return f"{file_path}::{symbol}"
    return f"{file_path}::global_scope"


# ---------------------------------------------------------------------------
# FST / JSpace route frame (Part 3)
# ---------------------------------------------------------------------------

_INTENT_KEYWORDS: dict[str, list[str]] = {
    "explain": ["explain", "why", "what", "inspect", "show", "understand"],
    "localize": ["find", "locate", "where", "isolate"],
    "code_refactor": ["refactor", "change", "modify", "update", "rewrite", "move"],
    "verify": ["verify", "test", "check", "validate"],
    "repair": ["repair", "fix", "heal", "debug"],
    "test_generate": ["generate test", "write test", "add test", "test gap"],
    "research_rank": ["research", "rank", "compare", "survey"],
}

_ARTIFACT_KEYWORDS: dict[str, list[str]] = {
    "python_module": [".py", "module", "function", "class", "method"],
    "test_file": ["test", "pytest", "spec"],
    "codemap": ["codemap", "topology", "graph"],
    "manifest": ["manifest", "config", "pyproject", "requirements"],
    "patch": ["patch", "diff", "change"],
    "documentation": [".md", "doc", "readme", "documentation"],
}

_ACTION_KEYWORDS: dict[str, list[str]] = {
    "inspect": ["inspect", "explain", "show", "why", "what"],
    "create": ["create", "add", "new", "generate", "write"],
    "modify": ["modify", "change", "update", "refactor", "edit"],
    "rank": ["rank", "compare", "sort"],
    "verify": ["verify", "test", "check", "validate"],
    "repair": ["repair", "fix", "heal", "debug"],
}

_SCOPE_KEYWORDS: dict[str, list[str]] = {
    "symbol": ["symbol", "function", "method", "class", "def "],
    "file": ["file", "path", "module"],
    "capsule": ["capsule", "act", "task"],
    "subsystem": ["subsystem", "arena", "component", "system"],
    "repo": ["repo", "repository", "all", "everything"],
}


def _match_keywords(text: str, table: dict[str, list[str]]) -> str:
    """Return the best-matching key from table based on keyword presence in text."""
    text_lower = text.lower()
    best_key = ""
    best_score = 0
    for key, keywords in table.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > best_score:
            best_score = score
            best_key = key
    return best_key


def _assess_risk(node: dict[str, Any], codemap: dict[str, Any]) -> str:
    """Assess risk level from node metadata and CODEMAP topology."""
    file_path = str(node.get("file_path", ""))
    file_index = codemap.get("topology", {}).get("file_index", {})
    entry = file_index.get(file_path, {})
    degree = int(entry.get("degree", 0))
    node_count = int(entry.get("node_count", 0))
    if degree > 200 or node_count > 100:
        return "high"
    if degree > 50 or node_count > 30:
        return "medium"
    return "low"


def _assess_grounding(node: dict[str, Any], codemap: dict[str, Any]) -> str:
    """Assess grounding level."""
    file_path = str(node.get("file_path", ""))
    if not file_path:
        return "none"
    files = codemap.get("files", [])
    file_exists = any(f.get("path") == file_path for f in files if isinstance(f, dict))
    if not file_exists:
        return "none"
    symbol = str(node.get("symbol", ""))
    if symbol:
        si = codemap.get("symbol_index", {})
        sym_exists = symbol in si
        if sym_exists:
            # Check for tests
            stem = Path(file_path).stem
            test_candidates = [f"test_{stem}.py", f"tests/test_{stem}.py"]
            tests_exist = any(
                any(f.get("path") == tc for f in files if isinstance(f, dict))
                for tc in test_candidates
            )
            if tests_exist:
                return "codemap_grounded"
            return "symbol_exists"
        return "file_exists"
    return "file_exists"


def _assess_tests(node: dict[str, Any], codemap: dict[str, Any]) -> str:
    """Assess test status."""
    file_path = str(node.get("file_path", ""))
    if not file_path:
        return "none"
    stem = Path(file_path).stem
    files = codemap.get("files", [])
    test_candidates = [f"test_{stem}.py", f"tests/test_{stem}.py", f"test_{stem.replace('aura_', '')}.py"]
    for tc in test_candidates:
        if any(f.get("path") == tc for f in files if isinstance(f, dict)):
            return "existing"
    return "required"


def _assess_quality(command: str) -> str:
    lowered = command.lower()
    if "fast" in lowered or "quick" in lowered:
        return "fast"
    if "accuracy" in lowered or "exact" in lowered:
        return "accuracy_first"
    if "verifier" in lowered or "verify" in lowered:
        return "verifier_required"
    return "balanced"


def _assess_cost(node: dict[str, Any]) -> str:
    """Cost assessment — no model needed for inspection."""
    return "no_model"


def _determine_route(intent: str, grounding: str, tests: str, risk: str) -> str:
    """Determine the FST route from intent/grounding/tests/risk."""
    if grounding == "none":
        return "BLOCKED_WITH_REASON"
    if intent == "code_refactor" and tests == "required":
        return "TEST_GAP_FILL"
    if intent == "code_refactor" and grounding in ("codemap_grounded", "full"):
        return "BUILDER_PATCH"
    if intent == "verify":
        return "VERIFY_ONLY"
    if intent in ("explain", "research_rank"):
        return "PLAN_ONLY"
    if intent == "localize":
        return "LOCALIZE_FIRST"
    if intent == "repair":
        return "BUILDER_PATCH"
    if risk == "high" and intent in ("code_refactor", "modify"):
        return "BLOCKED_WITH_REASON"
    return "PLAN_ONLY"


def route_node_command(
    command: str,
    selected_node_ids: list[str] | None = None,
    current_workspace: dict[str, Any] | None = None,
    repo_root: str | Path = ".",
) -> dict[str, Any]:
    """Map a broad node command into an FST/JSpace route frame.

    Returns a route frame dict with intent, artifact, action, scope, risk,
    grounding, tests, quality, cost, route, and next_state.
    JSpace/FST remain advisory only — never patch authority.
    """
    cmd_text = str(command or "").strip()
    intent = _match_keywords(cmd_text, _INTENT_KEYWORDS) or "explain"
    artifact = _match_keywords(cmd_text, _ARTIFACT_KEYWORDS) or "python_module"
    action = _match_keywords(cmd_text, _ACTION_KEYWORDS) or "inspect"
    scope = _match_keywords(cmd_text, _SCOPE_KEYWORDS) or "symbol"

    # Assess from selected nodes / workspace
    root = Path(repo_root).resolve()
    codemap = _load_codemap(root)
    risk = "low"
    grounding = "none"
    tests = "none"
    if selected_node_ids:
        # Use first selected node for assessment
        nid = selected_node_ids[0]
        node = _resolve_node_from_topology_or_codemap(nid, codemap, current_workspace)
        if node:
            risk = _assess_risk(node, codemap)
            grounding = _assess_grounding(node, codemap)
            tests = _assess_tests(node, codemap)
    elif current_workspace:
        files = current_workspace.get("files", [])
        if files:
            grounding = "codemap_grounded" if files else "none"

    quality = _assess_quality(cmd_text)
    cost = "no_model" if intent in ("explain", "localize") else "local_first"
    route = _determine_route(intent, grounding, tests, risk)

    # Next state mapping
    next_state_map = {
        "BLOCKED_WITH_REASON": "BLOCKED",
        "TEST_GAP_FILL": "NEED_TEST",
        "BUILDER_PATCH": "HUMAN_GATE",
        "VERIFY_ONLY": "VERIFY_ONLY",
        "PLAN_ONLY": "PLAN_ONLY",
        "LOCALIZE_FIRST": "LOCALIZE_FIRST",
    }
    next_state = next_state_map.get(route, "HUMAN_GATE")

    frame = {
        "intent": intent,
        "artifact": artifact,
        "action": action,
        "scope": scope,
        "risk": risk,
        "grounding": grounding,
        "tests": tests,
        "quality": quality,
        "cost": cost,
        "route": route,
        "next_state": next_state,
    }

    # Attach advisory JSpace state if available
    try:
        from aura_jspace_codec import build_jspace_packet, active_concepts_from_packet

        jpacket = build_jspace_packet(frame, {"route": route, "model": cost, "context": "SUMMARY", "reason": "route_valid"})
        jstate = active_concepts_from_packet(jpacket)
        frame["jspace_state"] = jstate.to_dict()
        frame["jspace_packet"] = jpacket.packet
    except Exception:
        frame["jspace_state"] = {}
        frame["jspace_packet"] = ""

    return frame


# ---------------------------------------------------------------------------
# Node resolution helpers
# ---------------------------------------------------------------------------


def _resolve_node_from_topology_or_codemap(
    node_id: str,
    codemap: dict[str, Any],
    current_workspace: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Resolve a node_id to a node dict from workspace, topology, or CODEMAP."""
    if not node_id:
        return None

    # 1. Check current workspace nodes
    if current_workspace:
        ws_nodes = current_workspace.get("nodes", [])
        if isinstance(ws_nodes, list):
            for n in ws_nodes:
                if isinstance(n, dict) and n.get("id") == node_id:
                    return n

    # 2. Parse node_id to extract file_path and symbol
    file_path, symbol = _parse_node_id(node_id)

    # 3. Check CODEMAP files
    files = codemap.get("files", [])
    for f in files:
        if isinstance(f, dict) and f.get("path") == file_path:
            # Found the file — build a minimal node dict
            node: dict[str, Any] = {
                "id": node_id,
                "file_path": file_path,
                "symbol": symbol,
                "kind": "file",
                "line_range": [],
            }
            # If symbol, look up in symbol_index
            if symbol:
                si = codemap.get("symbol_index", {})
                occurrences = si.get(symbol, [])
                for occ in occurrences:
                    if isinstance(occ, dict) and occ.get("file") == file_path:
                        node["kind"] = occ.get("kind", "function")
                        node["line_range"] = [int(occ.get("line", 0)), int(occ.get("end_line", 0))]
                        node["semantic_id"] = occ.get("semantic_id", "")
                        node["signature_hash"] = occ.get("signature_hash", "")
                        break
            return node

    # 4. Unresolved
    return None


def _parse_node_id(node_id: str) -> tuple[str, str]:
    """Parse a node_id like 'path/to/file.py::symbol' into (file_path, symbol)."""
    if "::" in node_id:
        parts = node_id.split("::", 1)
        file_path = parts[0]
        symbol = parts[1] if parts[1] != "global_scope" else ""
        return file_path, symbol
    return node_id, ""


# ---------------------------------------------------------------------------
# Relationship discovery
# ---------------------------------------------------------------------------


def _find_relationships(
    node: dict[str, Any],
    codemap: dict[str, Any],
) -> dict[str, list[str]]:
    """Find topology neighbors, callers, callees, tests, docs for a node."""
    file_path = str(node.get("file_path", ""))
    symbol = str(node.get("symbol", ""))
    relationships: dict[str, list[str]] = {
        "contains": [],
        "calls": [],
        "called_by": [],
        "neighbors": [],
        "tests": [],
        "docs": [],
        "commands": [],
        "related_concepts": [],
    }

    if not file_path:
        return relationships

    file_index = codemap.get("topology", {}).get("file_index", {})
    entry = file_index.get(file_path, {})
    neighbor_files = entry.get("neighbor_files", []) or []
    relationships["neighbors"] = [str(n) for n in neighbor_files[:20]]

    # Symbols contained in this file
    file_symbols = entry.get("symbols", []) or []
    if file_symbols:
        relationships["contains"] = [str(s) for s in file_symbols[:20]]
    # Also from symbol_index
    si = codemap.get("symbol_index", {})
    if not symbol:  # file-level node — list contained symbols
        for sym_name, occurrences in si.items():
            if not isinstance(occurrences, list):
                continue
            for occ in occurrences:
                if isinstance(occ, dict) and occ.get("file") == file_path:
                    if sym_name not in relationships["contains"]:
                        relationships["contains"].append(sym_name)
                    break

    # Calls: symbols that this file/symbol calls (approximated by neighbor files)
    # Called by: files that import/reference this file (reverse neighbors)
    for other_path, other_entry in file_index.items():
        if other_path == file_path:
            continue
        other_neighbors = other_entry.get("neighbor_files", []) or []
        if file_path in other_neighbors and other_path not in relationships["called_by"]:
            relationships["called_by"].append(other_path)
    relationships["called_by"] = relationships["called_by"][:20]

    # Calls = forward neighbors (simplified)
    relationships["calls"] = list(relationships["neighbors"])[:20]

    # Tests: find test files for this file
    stem = Path(file_path).stem
    files = codemap.get("files", [])
    test_candidates = [
        f"test_{stem}.py",
        f"tests/test_{stem}.py",
        f"test_{stem.replace('aura_', '')}.py",
    ]
    for tc in test_candidates:
        if any(f.get("path") == tc for f in files if isinstance(f, dict)):
            relationships["tests"].append(tc)

    # Docs: .md/.rst files that mention this file or symbol
    for f in files:
        if isinstance(f, dict):
            fp = str(f.get("path", ""))
            if fp.endswith(".md") or fp.endswith(".rst"):
                # Check if doc filename relates to the concept
                file_stem = Path(file_path).stem.lower().replace("aura_", "")
                doc_stem = Path(fp).stem.lower()
                if file_stem and (file_stem in doc_stem or doc_stem in file_stem):
                    relationships["docs"].append(fp)

    # Commands: from command_index
    command_index = codemap.get("command_index", {})
    for cmd, locations in command_index.items():
        if isinstance(locations, dict):
            cmd_files = locations.get("files", [])
            if file_path in cmd_files:
                relationships["commands"].append(str(cmd))
    relationships["commands"] = relationships["commands"][:15]

    return relationships


# ---------------------------------------------------------------------------
# Risk assessment
# ---------------------------------------------------------------------------


def _assess_risks(node: dict[str, Any], codemap: dict[str, Any], relationships: dict[str, list[str]]) -> dict[str, Any]:
    """Assess risk factors for a node."""
    file_path = str(node.get("file_path", ""))
    file_index = codemap.get("topology", {}).get("file_index", {})
    entry = file_index.get(file_path, {})
    degree = int(entry.get("degree", 0))
    node_count = int(entry.get("node_count", 0))
    files = codemap.get("files", [])
    file_entry = next((f for f in files if isinstance(f, dict) and f.get("path") == file_path), {})
    file_lines = int(file_entry.get("lines", 0))

    risks: dict[str, Any] = {
        "missing_tests": len(relationships.get("tests", [])) == 0 and file_path.endswith(".py"),
        "high_fan_in": degree > 200,
        "high_fan_out": len(relationships.get("neighbors", [])) > 20,
        "missing_grounding": not file_path,
        "large_file": file_lines > 1000,
        "hub_file": degree > 100,
        "degree": degree,
        "file_lines": file_lines,
        "severity": "low",
    }

    # Determine overall severity
    high_count = sum(1 for k, v in risks.items() if isinstance(v, bool) and v and k in ("high_fan_in", "hub_file"))
    med_count = sum(1 for k, v in risks.items() if isinstance(v, bool) and v and k in ("large_file", "high_fan_out", "missing_tests"))
    if high_count > 0:
        risks["severity"] = "high"
    elif med_count > 0:
        risks["severity"] = "medium"
    return risks


# ---------------------------------------------------------------------------
# why_here grounding path
# ---------------------------------------------------------------------------


def _build_why_here(
    node: dict[str, Any],
    node_origin: str,
    codemap: dict[str, Any],
    relationships: dict[str, list[str]],
    current_workspace: dict[str, Any] | None = None,
) -> str:
    """Build a human-readable explanation of why this node is here."""
    file_path = str(node.get("file_path", ""))
    symbol = str(node.get("symbol", ""))
    parts: list[str] = []

    if node_origin == ORIGIN_EXACT_TOPOLOGY:
        parts.append("This node is an exact topology node — present in the currently loaded arena topology.")
    elif node_origin == ORIGIN_CODEMAP_PROJECTED:
        parts.append("This node is a CODEMAP-projected node — a real file/symbol from .aura/CODEMAP.json projected into the current visual workspace.")
    elif node_origin == ORIGIN_GHOST_HYPOTHESIS:
        parts.append("This is a ghost hypothesis edge — human-created, never patch authority.")
    elif node_origin == ORIGIN_UNRESOLVED:
        parts.append("This node is an unresolved candidate — NEEDS_GROUNDING. No CODEMAP match found.")
        return " ".join(parts)

    # Grounding path
    if file_path:
        parts.append(f"Grounded by CODEMAP file path: {file_path}.")
    if symbol:
        parts.append(f"Symbol match: {symbol}.")
    if relationships.get("neighbors"):
        parts.append(f"Topology neighbors: {', '.join(relationships['neighbors'][:3])}...")
    if relationships.get("tests"):
        parts.append(f"Test relation: {', '.join(relationships['tests'][:2])}.")
    if relationships.get("docs"):
        parts.append(f"Doc relation: {', '.join(relationships['docs'][:2])}.")
    if current_workspace and current_workspace.get("concept"):
        parts.append(f"Matched alias for concept workspace: {current_workspace['concept']}.")

    return " ".join(parts)


# ---------------------------------------------------------------------------
# Core: inspect_node
# ---------------------------------------------------------------------------


def inspect_node(
    node_id: str,
    repo_root: str | Path = ".",
    current_workspace: dict[str, Any] | None = None,
    topology: dict[str, Any] | None = None,
) -> NodeIntelligencePacket:
    """Produce a grounded NodeIntelligencePacket for a node.

    Resolves the node against current topology, then CODEMAP file paths and
    symbol_index. Identifies origin, pulls file/symbol/line range/digest/
    signature hash from CODEMAP, finds topology neighbors, tests, docs,
    and produces why_here + safe next actions.
    """
    root = Path(repo_root).resolve()
    codemap = _load_codemap(root)

    node_id = str(node_id or "").strip()
    if not node_id:
        pkt = NodeIntelligencePacket(
            node_origin=ORIGIN_UNRESOLVED,
            why_here="No node ID provided. NEEDS_GROUNDING.",
            notes=["No node_id given to inspect_node."],
        )
        return pkt

    # Determine origin: exact topology vs CODEMAP-projected
    node: dict[str, Any] | None = None
    node_origin = ORIGIN_UNRESOLVED

    # 1. Check current topology
    if topology:
        topo_nodes = topology.get("nodes", [])
        for tn in topo_nodes:
            if isinstance(tn, dict) and tn.get("id") == node_id:
                node = tn
                meta = tn.get("metadata", {}) or {}
                if meta.get("node_origin") == ORIGIN_CODEMAP_PROJECTED or meta.get("projected_from_codemap"):
                    node_origin = ORIGIN_CODEMAP_PROJECTED
                else:
                    node_origin = ORIGIN_EXACT_TOPOLOGY
                break

    # 2. Check current workspace nodes
    if node is None and current_workspace:
        ws_nodes = current_workspace.get("nodes", [])
        if isinstance(ws_nodes, list):
            for wn in ws_nodes:
                if isinstance(wn, dict) and wn.get("id") == node_id:
                    node = wn
                    meta = wn.get("metadata", {}) or {}
                    if meta.get("node_origin") == ORIGIN_CODEMAP_PROJECTED or meta.get("projected_from_codemap"):
                        node_origin = ORIGIN_CODEMAP_PROJECTED
                    else:
                        node_origin = ORIGIN_EXACT_TOPOLOGY
                    break

    # 3. Resolve from CODEMAP
    if node is None:
        node = _resolve_node_from_topology_or_codemap(node_id, codemap, current_workspace)
        if node:
            node_origin = ORIGIN_CODEMAP_PROJECTED

    # 4. Still unresolved
    if node is None:
        pkt = NodeIntelligencePacket(
            node_id=node_id,
            node_origin=ORIGIN_UNRESOLVED,
            why_here="This node could not be grounded in CODEMAP or current topology. NEEDS_GROUNDING.",
            grounding_source="",
            entity_exists=False,
            confidence=0.0,
            next_actions=["show ST3GG", "show Coding Arena", "what Aura tools can help here"],
            notes=["Unresolved candidate — no CODEMAP match found."],
        )
        return pkt

    # Extract grounding facts
    file_path = str(node.get("file_path", ""))
    symbol = str(node.get("symbol", ""))
    kind = str(node.get("kind", node.get("node_type", "")))
    line_range = list(node.get("line_range", []) or [])
    digest8 = str(node.get("digest8", "") or node.get("metadata", {}).get("digest8", ""))
    semantic_id = str(node.get("semantic_id", "") or node.get("metadata", {}).get("semantic_id", ""))
    signature_hash = str(node.get("signature_hash", "") or node.get("metadata", {}).get("signature_hash", ""))

    # Enrich from CODEMAP if missing
    if file_path and (not line_range or not signature_hash):
        si = codemap.get("symbol_index", {})
        if symbol and symbol in si:
            for occ in si[symbol]:
                if isinstance(occ, dict) and occ.get("file") == file_path:
                    if not line_range:
                        line_range = [int(occ.get("line", 0)), int(occ.get("end_line", 0))]
                    if not semantic_id:
                        semantic_id = str(occ.get("semantic_id", ""))
                    if not signature_hash:
                        signature_hash = str(occ.get("signature_hash", ""))
                    break
    if not digest8 and file_path:
        digest8 = _short_hash(file_path, size=8)

    # Entity exists check
    files = codemap.get("files", [])
    entity_exists = any(f.get("path") == file_path for f in files if isinstance(f, dict)) if file_path else False

    # Relationships
    relationships = _find_relationships(node, codemap)

    # Risks
    risk = _assess_risks(node, codemap, relationships)

    # why_here
    why_here = _build_why_here(node, node_origin, codemap, relationships, current_workspace)

    # FST route frame
    fst_route = route_node_command(
        "inspect node",
        selected_node_ids=[node_id],
        current_workspace=current_workspace,
        repo_root=root,
    )

    # JSpace state (advisory)
    jspace_state = fst_route.get("jspace_state", {}) if isinstance(fst_route, dict) else {}

    # Recommended affordances (lazy import to avoid circular dependency)
    recommended_affordances: list[dict[str, Any]] = []
    try:
        from aura_affordance_directory import find_affordances

        affordance_result = find_affordances(
            objective=f"inspect {file_path}::{symbol}" if symbol else f"inspect {file_path}",
            target_files=[file_path] if file_path else None,
            target_symbols=[symbol] if symbol else None,
            selected_node_ids=[node_id],
            current_workspace=current_workspace,
            repo_root=root,
            top_k=5,
        )
        recommended_affordances = affordance_result.get("recommended_affordances", [])
    except Exception:
        pass

    # Next actions
    next_actions = [
        "explain selected",
        "expand selected",
        "show callers",
        "show callees",
        "show tests for selected",
        "show risks",
        "what would break if this changed",
        "what Aura tools can help here",
    ]
    if node_origin == ORIGIN_CODEMAP_PROJECTED:
        next_actions.insert(0, "show exact source for selected")

    # Confidence
    confidence = 0.0
    if entity_exists:
        confidence += 0.4
    if line_range:
        confidence += 0.2
    if signature_hash:
        confidence += 0.2
    if relationships.get("neighbors"):
        confidence += 0.1
    if node_origin == ORIGIN_EXACT_TOPOLOGY:
        confidence += 0.1

    notes: list[str] = []
    if node_origin == ORIGIN_CODEMAP_PROJECTED:
        notes.append("CODEMAP-projected node: real file/symbol, visual projection only.")
    if risk.get("severity") == "high":
        notes.append("High risk: review before any changes.")

    pkt = NodeIntelligencePacket(
        node_id=node_id,
        node_origin=node_origin,
        why_here=why_here,
        grounding_source=".aura/CODEMAP.json" if entity_exists else "",
        file_path=file_path,
        symbol=symbol,
        kind=kind,
        line_range=line_range,
        digest8=digest8,
        semantic_id=semantic_id,
        signature_hash=signature_hash,
        entity_exists=entity_exists,
        patch_authority=False,
        vsa_patch_authority=False,
        relationships=relationships,
        risk=risk,
        jspace_state=jspace_state,
        fst_route=fst_route,
        recommended_affordances=recommended_affordances,
        next_actions=next_actions,
        confidence=confidence,
        notes=notes,
    )
    return pkt


# ---------------------------------------------------------------------------
# Core: expand_node (lazy expansion)
# ---------------------------------------------------------------------------


def expand_node(
    node_id: str,
    expansion_mode: str = "balanced",
    depth: int = 1,
    repo_root: str | Path = ".",
    current_workspace: dict[str, Any] | None = None,
    topology: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Lazily expand a node by finding related nodes/edges.

    Expansion modes:
    - children: contained functions/classes/methods
    - callers: incoming callers/neighbor files
    - callees: outgoing dependencies
    - tests: related tests
    - docs: related docs
    - risks: verifier/risk facts
    - full: all available grounded rings
    - balanced: readable mixed subset

    Returns additional nodes, additional links, truth packet,
    node intelligence packet, visual update, and next actions.
    """
    root = Path(repo_root).resolve()
    codemap = _load_codemap(root)
    node_id = str(node_id or "").strip()
    expansion_mode = str(expansion_mode or "balanced").strip()

    # Get the intelligence packet for this node
    pkt = inspect_node(
        node_id,
        repo_root=root,
        current_workspace=current_workspace,
        topology=topology,
    )

    if pkt.node_origin == ORIGIN_UNRESOLVED:
        return {
            "ok": True,
            "answer": f"Cannot expand unresolved node '{node_id}'. NEEDS_GROUNDING.",
            "additional_nodes": [],
            "additional_links": [],
            "truth_packet": pkt.to_truth_packet(),
            "node_intelligence": pkt.to_dict(),
            "visual_update": {
                "highlighted_node_ids": [],
                "hidden_node_ids": [],
                "selected_node_ids": [node_id],
                "ghost_edges": [],
                "labels": {},
                "ui_hints": ["needs_grounding"],
            },
            "next_actions": ["show ST3GG", "show Coding Arena", "what Aura tools can help here"],
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    file_path = pkt.file_path
    symbol = pkt.symbol
    rel = pkt.relationships

    additional_nodes: list[dict[str, Any]] = []
    additional_links: list[dict[str, Any]] = []

    def _add_file_node(fp: str, kind: str = "file") -> None:
        if not fp:
            return
        nid = _stable_node_id(fp)
        if nid == node_id:
            return
        # Check if already in additional_nodes
        if any(n.get("id") == nid for n in additional_nodes):
            return
        digest8 = _short_hash(fp, size=8)
        additional_nodes.append({
            "id": nid,
            "label": Path(fp).name,
            "node_type": kind,
            "file_path": fp,
            "symbol": "",
            "kind": kind,
            "line_range": [],
            "tokens_est": 0,
            "status": "expanded",
            "color": "#4f8cff" if kind == "file" else "#38c98b",
            "x": 0.0, "y": 0.0, "z": 0.0,
            "digest8": digest8,
            "metadata": {
                "node_origin": ORIGIN_CODEMAP_PROJECTED,
                "projected_from_codemap": True,
                "grounding_source": ".aura/CODEMAP.json",
                "visual_projection_only": True,
                "entity_exists": True,
                "patch_authority": False,
            },
        })
        additional_links.append({
            "source": node_id,
            "target": nid,
            "link_type": "neighbor",
            "weight": 0.8,
            "status": "known",
            "label": "neighbor",
            "metadata": {
                "edge_origin": ORIGIN_INFERRED_EDGE,
                "inference_source": f"expand_{expansion_mode}",
            },
        })

    def _add_symbol_node(fp: str, sym: str, kind: str = "function") -> None:
        if not fp or not sym:
            return
        nid = _stable_node_id(fp, sym)
        if nid == node_id:
            return
        if any(n.get("id") == nid for n in additional_nodes):
            return
        # Get line range from CODEMAP
        lr: list[int] = []
        sig_hash = ""
        si = codemap.get("symbol_index", {})
        if sym in si:
            for occ in si[sym]:
                if isinstance(occ, dict) and occ.get("file") == fp:
                    lr = [int(occ.get("line", 0)), int(occ.get("end_line", 0))]
                    sig_hash = str(occ.get("signature_hash", ""))
                    break
        additional_nodes.append({
            "id": nid,
            "label": sym,
            "node_type": kind,
            "file_path": fp,
            "symbol": sym,
            "kind": kind,
            "line_range": lr,
            "tokens_est": 0,
            "status": "expanded",
            "color": "#38c98b" if kind == "function" else "#f2b84b",
            "x": 0.0, "y": 0.0, "z": 0.0,
            "signature_hash": sig_hash,
            "metadata": {
                "node_origin": ORIGIN_CODEMAP_PROJECTED,
                "projected_from_codemap": True,
                "grounding_source": ".aura/CODEMAP.json",
                "visual_projection_only": True,
                "entity_exists": True,
                "patch_authority": False,
            },
        })
        additional_links.append({
            "source": node_id,
            "target": nid,
            "link_type": "contains" if expansion_mode == "children" else "related",
            "weight": 0.7,
            "status": "known",
            "label": "contains" if expansion_mode == "children" else "related",
            "metadata": {
                "edge_origin": ORIGIN_INFERRED_EDGE,
                "inference_source": f"expand_{expansion_mode}",
            },
        })

    # Expansion based on mode
    if expansion_mode == "children":
        # Contained functions/classes/methods
        for sym in rel.get("contains", [])[:20]:
            kind = "class" if sym[0].isupper() else "function"
            _add_symbol_node(file_path, sym, kind)

    elif expansion_mode == "callers":
        for fp in rel.get("called_by", [])[:20]:
            _add_file_node(fp, "file")

    elif expansion_mode == "callees":
        for fp in rel.get("calls", [])[:20]:
            _add_file_node(fp, "file")

    elif expansion_mode == "tests":
        for fp in rel.get("tests", [])[:10]:
            _add_file_node(fp, "test")

    elif expansion_mode == "docs":
        for fp in rel.get("docs", [])[:10]:
            _add_file_node(fp, "doc")

    elif expansion_mode == "risks":
        # Return risk facts as a special expansion
        risk = pkt.risk
        return {
            "ok": True,
            "answer": f"Risk assessment for {file_path}: severity={risk.get('severity', 'low')}. "
            f"missing_tests={risk.get('missing_tests', False)}, high_fan_in={risk.get('high_fan_in', False)}, "
            f"large_file={risk.get('large_file', False)}, hub_file={risk.get('hub_file', False)}.",
            "additional_nodes": [],
            "additional_links": [],
            "truth_packet": pkt.to_truth_packet(),
            "node_intelligence": pkt.to_dict(),
            "visual_update": {
                "highlighted_node_ids": [node_id],
                "hidden_node_ids": [],
                "selected_node_ids": [node_id],
                "ghost_edges": [],
                "labels": {node_id: f"risk:{risk.get('severity', 'low')}"},
                "ui_hints": [f"risk_{risk.get('severity', 'low')}"],
                "risk_badges": risk,
            },
            "next_actions": ["show tests for selected", "what would break if this changed", "prepare agent task"],
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    elif expansion_mode == "full":
        # All available grounded rings
        for sym in rel.get("contains", [])[:15]:
            kind = "class" if sym[0].isupper() else "function"
            _add_symbol_node(file_path, sym, kind)
        for fp in rel.get("called_by", [])[:10]:
            _add_file_node(fp, "file")
        for fp in rel.get("calls", [])[:10]:
            _add_file_node(fp, "file")
        for fp in rel.get("tests", [])[:5]:
            _add_file_node(fp, "test")
        for fp in rel.get("docs", [])[:5]:
            _add_file_node(fp, "doc")

    else:  # balanced (default)
        # Readable mixed subset
        for sym in rel.get("contains", [])[:8]:
            kind = "class" if sym[0].isupper() else "function"
            _add_symbol_node(file_path, sym, kind)
        for fp in rel.get("called_by", [])[:5]:
            _add_file_node(fp, "file")
        for fp in rel.get("calls", [])[:5]:
            _add_file_node(fp, "file")
        for fp in rel.get("tests", [])[:3]:
            _add_file_node(fp, "test")

    # Build visual update
    new_node_ids = [n["id"] for n in additional_nodes]
    highlighted = [node_id] + new_node_ids

    visual_update = {
        "highlighted_node_ids": highlighted,
        "hidden_node_ids": [],
        "selected_node_ids": [node_id],
        "ghost_edges": [],
        "labels": {nid: f"expanded:{expansion_mode}" for nid in new_node_ids},
        "ui_hints": [f"expanded_{expansion_mode}"],
        "additional_nodes": additional_nodes,
        "additional_links": additional_links,
    }

    # Truth packet
    truth = pkt.to_truth_packet()
    truth["expanded_node_ids"] = new_node_ids
    truth["expansion_mode"] = expansion_mode

    # Recommended read-slice command instead of dumping source
    if file_path and symbol and pkt.line_range:
        read_slice_cmd = f"aura_read_slice --file {file_path} --symbol {symbol}"
    elif file_path and pkt.line_range:
        read_slice_cmd = f"aura_read_slice --file {file_path} --line_start {pkt.line_range[0]} --line_end {pkt.line_range[1]}"
    elif file_path:
        read_slice_cmd = f"aura_read_slice --file {file_path}"
    else:
        read_slice_cmd = ""

    answer = (
        f"Expanded '{node_id}' ({expansion_mode} mode): "
        f"{len(additional_nodes)} additional node(s), {len(additional_links)} link(s). "
        f"Origin: {pkt.node_origin}. "
    )
    if read_slice_cmd:
        answer += f"For exact source, use: {read_slice_cmd}"

    next_actions = [
        "explain selected",
        "show callers",
        "show callees",
        "show tests for selected",
        "show risks",
        "what would break if this changed",
        "what Aura tools can help here",
    ]

    return {
        "ok": True,
        "answer": answer,
        "additional_nodes": additional_nodes,
        "additional_links": additional_links,
        "truth_packet": truth,
        "node_intelligence": pkt.to_dict(),
        "visual_update": visual_update,
        "next_actions": next_actions,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        "read_slice_command": read_slice_cmd,
    }


# ---------------------------------------------------------------------------
# why_is_node_here — convenience function
# ---------------------------------------------------------------------------


def why_is_node_here(
    node_id: str,
    repo_root: str | Path = ".",
    current_workspace: dict[str, Any] | None = None,
    topology: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Explain the grounding path for a node — why it is here."""
    pkt = inspect_node(
        node_id,
        repo_root=repo_root,
        current_workspace=current_workspace,
        topology=topology,
    )
    return {
        "ok": True,
        "answer": pkt.why_here,
        "node_id": node_id,
        "node_origin": pkt.node_origin,
        "grounding_source": pkt.grounding_source,
        "entity_exists": pkt.entity_exists,
        "file_path": pkt.file_path,
        "symbol": pkt.symbol,
        "line_range": pkt.line_range,
        "digest8": pkt.digest8,
        "signature_hash": pkt.signature_hash,
        "confidence": pkt.confidence,
        "truth_packet": pkt.to_truth_packet(),
        "node_intelligence": pkt.to_dict(),
        "next_actions": [
            "expand selected",
            "show callers",
            "show callees",
            "show tests for selected",
            "what Aura tools can help here",
        ],
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
