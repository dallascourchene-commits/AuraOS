"""
Aura Topology Health — validates CODEMAP topology integrity before graph operations.

Checks CODEMAP topology, symbol index, command index, understand graph, and
detects regressions. If topology is zero-node or unavailable, blocks change
graph generation and routes to NEED_TOPOLOGY_REPAIR.

Dependencies: stdlib only. All Aura imports are lazy.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
TOPOLOGY_HEALTH_VERSION = "AURA_TOPOLOGY_HEALTH_V1"


def _load_codemap(repo_root: Path) -> dict[str, Any]:
    path = repo_root / ".aura" / "CODEMAP.json"
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def check_codemap_health(repo_root: str | Path = ".") -> dict[str, Any]:
    root = Path(repo_root).resolve()
    cm = _load_codemap(root)
    coverage = cm.get("coverage", {})
    summary = cm.get("summary", {})
    file_count = int(
        summary.get("file_count")
        or coverage.get("included_file_count")
        or coverage.get("repo_file_count")
        or 0
    )
    if not file_count and isinstance(cm.get("files"), list):
        file_count = len(cm["files"])
    topo = cm.get("topology", {})
    # Topology node/edge counts are in summary, not in topology.nodes
    topo_nodes = int(summary.get("topology_nodes", 0))
    topo_edges = int(summary.get("topology_edges", 0))
    topo_source = summary.get("topology_source", topo.get("source", "unknown"))
    fi = topo.get("file_index", {}) if isinstance(topo, dict) else {}
    neighbor_files = len(fi) > 0
    si = cm.get("symbol_index", {})
    ci = cm.get("command_index", {})
    ok = file_count > 0 and len(si) > 0
    return {
        "ok": ok, "codemap_file_count": file_count, "topology_source": topo_source,
        "topology_nodes": topo_nodes, "topology_edges": topo_edges,
        "symbol_index_count": len(si), "command_index_count": len(ci),
        "neighbor_files_available": neighbor_files,
        "exact_line_ranges_available": bool(si),
        "source_hashes_available": bool(fi),
        "tests_index_available": any("test" in str(k).lower() for k in si),
        "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def check_understand_graph_health(repo_root: str | Path = ".") -> dict[str, Any]:
    root = Path(repo_root).resolve()
    path = root / ".aura" / "understand_graph.json"
    present = path.exists()
    nodes = 0
    if present:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            nodes = len(data.get("nodes", []) or [])
        except Exception:
            pass
    return {"ok": present, "understand_graph_present": present,
             "understand_graph_nodes": nodes,
             "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def check_symbol_index_health(repo_root: str | Path = ".") -> dict[str, Any]:
    root = Path(repo_root).resolve()
    cm = _load_codemap(root)
    si = cm.get("symbol_index", {})
    ok = len(si) > 0
    has_line_ranges = any(
        isinstance(v, list) and v and isinstance(v[0], dict) and "line" in v[0]
        for v in si.values() if v
    )
    return {"ok": ok, "symbol_index_count": len(si),
            "has_line_ranges": has_line_ranges,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def check_command_index_health(repo_root: str | Path = ".") -> dict[str, Any]:
    root = Path(repo_root).resolve()
    cm = _load_codemap(root)
    ci = cm.get("command_index", {})
    return {"ok": len(ci) > 0, "command_index_count": len(ci),
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def detect_topology_regression(previous: dict | None = None, current: dict | None = None,
                               repo_root: str | Path = ".") -> dict[str, Any]:
    root = Path(repo_root).resolve()
    if current is None:
        current = check_codemap_health(root)
    baseline_loaded = False
    if previous is None:
        # Try loading baseline from .aura/topology_baseline.json
        baseline_path = root / ".aura" / "topology_baseline.json"
        try:
            if baseline_path.exists():
                import json
                with open(baseline_path, "r", encoding="utf-8") as f:
                    previous = json.load(f)
                    baseline_loaded = True
        except Exception:
            pass
    else:
        baseline_loaded = True
    if previous is None:
        # No persisted baseline available — use documented fallback baseline for zero-node regression detection
        # Fallback values are from commit 6f48c2f's known-good topology state
        previous = {"topology_nodes": 2203, "topology_edges": 2197, "topology_source": "fallback_baseline"}
    regressed = (
        current.get("topology_nodes", 0) == 0 and previous.get("topology_nodes", 0) > 0
    )
    return {"ok": not regressed, "regression_detected": regressed, "baseline_available": baseline_loaded,
            "previous": previous, "current": current,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def suggest_topology_repair(repo_root: str | Path = ".") -> dict[str, Any]:
    root = Path(repo_root).resolve()
    health = check_codemap_health(root)
    suggestions = []
    if health.get("topology_nodes", 0) == 0:
        suggestions.append("python aura_codebase_navigator.py --refresh-topology")
    if not health.get("neighbor_files_available"):
        suggestions.append("python aura_codebase_navigator.py --refresh-topology")
    if not health.get("source_hashes_available"):
        suggestions.append("python aura_codebase_navigator.py --refresh-topology")
    if not suggestions:
        suggestions.append("python aura_codebase_navigator.py --refresh .")
    return {"ok": True, "repair_command_suggestion": suggestions,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def topology_health_packet(repo_root: str | Path = ".") -> dict[str, Any]:
    root = Path(repo_root).resolve()
    cm_health = check_codemap_health(root)
    ug_health = check_understand_graph_health(root)
    si_health = check_symbol_index_health(root)
    ci_health = check_command_index_health(root)
    regression = detect_topology_regression(current=cm_health, repo_root=root)
    repair = suggest_topology_repair(root)
    topo_ok = cm_health.get("topology_nodes", 0) > 0
    next_gate = "NEED_TOPOLOGY_REPAIR" if not topo_ok else "WORKSPACE_OPENED"
    missing_reason = ""
    if not topo_ok:
        missing_reason = "Topology has 0 nodes. Run topology rebuild before graph operations."
    return {
        "ok": cm_health.get("ok", False) and si_health.get("ok", False),
        "version": TOPOLOGY_HEALTH_VERSION,
        "topology_source": cm_health.get("topology_source", "unknown"),
        "topology_nodes": cm_health.get("topology_nodes", 0),
        "topology_edges": cm_health.get("topology_edges", 0),
        "codemap_file_count": cm_health.get("codemap_file_count", 0),
        "symbol_index_count": cm_health.get("symbol_index_count", 0),
        "command_index_count": cm_health.get("command_index_count", 0),
        "understand_graph_present": ug_health.get("understand_graph_present", False),
        "neighbor_files_available": cm_health.get("neighbor_files_available", False),
        "exact_line_ranges_available": cm_health.get("exact_line_ranges_available", False),
        "source_hashes_available": cm_health.get("source_hashes_available", False),
        "tests_index_available": cm_health.get("tests_index_available", False),
        "regression_detected": regression.get("regression_detected", False),
        "missing_topology_reason": missing_reason,
        "repair_command_suggestion": repair.get("repair_command_suggestion", []),
        "next_gate": next_gate,
        "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
