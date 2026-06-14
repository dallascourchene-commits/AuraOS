#!/usr/bin/env python3
"""
generate_ai_router.py – Builds AURA_AI_ROUTER.md from live topology and PSML headers.

Usage:
    python3 generate_ai_router.py
    python3 generate_ai_router.py --output Aura_Memory/AURA_AI_ROUTER.md
    python3 generate_ai_router.py --topology path/to/live_topology_ast.json
"""

import argparse
import ast
import json
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

TOPOLOGY_PATH = "Aura_Memory/live_topology_ast.json"
LEXICON_PATH = "aura.lexc"
OUTPUT_MD = "AURA_AI_ROUTER.md"

# ── Task → File mapping table ────────────────────────────────────────────────
# This is the manual/static "intent index" – extend as the project grows.
TASK_MAPPING: Dict[str, Dict[str, Any]] = {
    "forage new papers": {
        "primary": "arxiv_forager.py",
        "secondary": ["aura_forager.py", "aura_ingest.py"],
        "key_functions": ["forage()", "_batch_fetch()", "ArXivForager"],
    },
    "resonate topology": {
        "primary": "aura_topology_analyzer.py",
        "secondary": ["liquid_fhrr.py", "Aura_Memory/live_topology_ast.json"],
        "key_functions": ["diagnose_fractures()", "compile_unified_graph()"],
    },
    "self-optimize a function": {
        "primary": "aura_self_optimize.py",
        "secondary": ["aura_router.py", "aura_incubator.py"],
        "key_functions": ["self_optimize()", "build_fix_task()"],
    },
    "render AR view": {
        "primary": "index.html",
        "secondary": ["pulse.py", "aura_topology_ws_bridge.py"],
        "key_functions": ["WebSocket TOPOLOGY_REQUEST", "AuraARWebSocketServer"],
    },
    "evolve constraint resolver": {
        "primary": "aura_governor.py",
        "secondary": ["aura_qdkt.py", "aura_crystallization.py"],
        "key_functions": ["hypertruth_crystallization_loop()", "get_qdkt()"],
    },
    "route llm request": {
        "primary": "aura_router.py",
        "secondary": ["aura_llm_egress.py", "aura_matrix_benchmark.py"],
        "key_functions": ["AutoRouter", "calibrate()", "route_task()"],
    },
    "manage memory palace": {
        "primary": "async_palace.py",
        "secondary": ["aura_attention_palace.py", "aura_hv_cache.py"],
        "key_functions": ["AsyncMemoryPalace", "store()", "retrieve()"],
    },
    "run blockchain ledger": {
        "primary": "aura_blockchain/node.py",
        "secondary": ["aura_blockchain/block.py", "aura_blockchain/consensus.py"],
        "key_functions": ["PhasorLedger", "mine_block()", "verify_chain()"],
    },
    "scan topology deep": {
        "primary": "aura_topological_scanner.py",
        "secondary": ["spatial_mapper.py", "aura_topology_manager.py"],
        "key_functions": ["compile_unified_graph()", "compile_topology_map()"],
    },
    "generate patch for code": {
        "primary": "aura_patcher.py",
        "secondary": ["aura_substrate.py", "aura_proxy_benchmark.py"],
        "key_functions": ["AuraSovereignPatcher", "apply_edit_plan()"],
    },
}


# ── Lexicon reader ────────────────────────────────────────────────────────────

def read_lexicon_states() -> Dict[str, str]:
    """Parse aura.lexc to get state→type mapping (simplified)."""
    if not os.path.exists(LEXICON_PATH):
        return {}
    states: Dict[str, str] = {}
    current_lexicon = ""
    with open(LEXICON_PATH, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line.startswith("!") or not line:
                continue
            lex_match = re.match(r"^LEXICON\s+(\w+)", line)
            if lex_match:
                current_lexicon = lex_match.group(1)
                continue
            if ":" in line:
                parts = line.split(":", 1)
                tag = parts[0].strip()
                if tag and current_lexicon:
                    shape = "Cube" if "CUBE" in line else ("Sphere" if "SPHERE" in line else "Node")
                    states[f"{current_lexicon}::{tag}"] = shape
    return states


# ── PSML header extractor ─────────────────────────────────────────────────────

def extract_psml_header(filepath: str) -> Dict[str, Any]:
    """
    Extract or auto-generate a minimal PSML header for a Python file.

    Priority order:
      1. [AURA_MASTER_KEY] block (AuraOS native format)
      2. [FILE HEADER] block (gist-style)
      3. AST fallback – function and class names
    """
    header: Dict[str, Any] = {
        "purpose": "",
        "dependencies": [],
        "primary_functions": [],
        "line_ranges": {},
    }

    if not os.path.exists(filepath):
        return header

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except OSError:
        return header

    # ── Try [AURA_MASTER_KEY] block ──────────────────────────────────────────
    mk_match = re.search(r"\[AURA_MASTER_KEY\](.*?)\[/AURA_MASTER_KEY\]", content, re.DOTALL)
    if mk_match:
        text = mk_match.group(1)
        deps_match = re.search(r"DEPENDENCIES:\s*(.+)", text)
        if deps_match:
            header["dependencies"] = [d.strip() for d in deps_match.group(1).split(",")][:8]
        funcs_match = re.search(r"FUNCTIONS:\s*(.+)", text)
        if funcs_match:
            header["primary_functions"] = [f.strip() for f in funcs_match.group(1).split(",")][:8]
        # Derive purpose from PWFST_ALIGNMENT + the first sentence after the block
        pwfst = re.search(r"PWFST_ALIGNMENT:\s*(.+)", text)
        if pwfst:
            header["purpose"] = pwfst.group(1).strip()
        # Also check the first non-empty line after [/AURA_MASTER_KEY]
        remaining = content[mk_match.end():].strip()
        first_line = remaining.split("\n")[0].strip() if remaining else ""
        if first_line and len(first_line) < 120:
            header["purpose"] = first_line.rstrip(".")

    # ── Try [FILE HEADER] block ──────────────────────────────────────────────
    elif "[FILE HEADER]" in content:
        fh_match = re.search(r'"""(.*?)"""', content, re.DOTALL)
        if fh_match and "[FILE HEADER]" in fh_match.group(1):
            text = fh_match.group(1)
            p = re.search(r"PURPOSE:\s*(.+?)(?:\n|$)", text)
            if p:
                header["purpose"] = p.group(1).strip()
            deps = re.findall(r"-\s*(.+?)\s*\(Type:", text)
            header["dependencies"] = deps[:8]
            funcs = re.findall(r"-\s*(.+?)\s*\(Node:", text)
            header["primary_functions"] = funcs[:8]

    # ── AST fallback ──────────────────────────────────────────────────────────
    if not header["primary_functions"]:
        try:
            tree = ast.parse(content)
            names: List[str] = []
            for node in ast.walk(tree):
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Skip private helpers (underscore prefix) to keep list concise
                    if not node.name.startswith("__"):
                        names.append(node.name)
            header["primary_functions"] = names[:8]
        except SyntaxError:
            pass

    if not header["purpose"]:
        header["purpose"] = "[TODO: add PSML header with PURPOSE field]"

    return header


def _extract_line_ranges(filepath: str, function_names: List[str]) -> Dict[str, int]:
    """Return {func_name: start_line} using AST for the given functions."""
    ranges: Dict[str, int] = {}
    if not os.path.exists(filepath):
        return ranges
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.name in function_names:
                    ranges[node.name] = node.lineno
    except (SyntaxError, OSError):
        pass
    return ranges


# ── Shared resource detector ──────────────────────────────────────────────────

def _detect_shared_resources(nodes: List[Dict], edges: List[Dict],
                              node_by_id: Dict[str, Dict]) -> Dict[str, List[str]]:
    """
    Detect shared resources (ports, databases, etc.) from topology nodes.
    Returns {resource_type: [name, ...]}.
    """
    resources: Dict[str, List[str]] = defaultdict(list)
    for n in nodes:
        label = n.get("label", "")
        nid = n.get("id", "")
        if any(kw in label.lower() or kw in nid.lower()
               for kw in ("port", "socket", "udp", "tcp")):
            resources["Network ports"].append(label)
        if any(kw in label.lower() or kw in nid.lower()
               for kw in ("sqlite", "database", ".db", "ledger")):
            resources["SQLite / DB"].append(label)
        if any(kw in label.lower() or kw in nid.lower()
               for kw in ("json", "cache", "memory", "store")):
            resources["Memory / Cache"].append(label)
    return resources


# ── Main builder ──────────────────────────────────────────────────────────────

def build_router_md(topology_path: str = TOPOLOGY_PATH,
                    output_path: str = OUTPUT_MD) -> str:
    """
    Generate the full AURA_AI_ROUTER.md content.

    If topology_path does not exist yet, a minimal skeleton is produced so the
    file is always valid Markdown even before the first `!topology` run.
    """
    lines: List[str] = []

    lines.append("# AURA AI ROUTER – v4.01\n")
    lines.append("> **Read-only** navigation index for AI agents. Regenerate with "
                 "`python3 generate_ai_router.py` or `!topology deep`.\n")

    # ── Task → File mapping table ─────────────────────────────────────────────
    lines.append("## Task → File Mapping\n")
    lines.append("| Task / Intent | Primary File | Secondary Files | Key Functions |")
    lines.append("|---------------|:-------------|:----------------|:--------------|")
    for task, info in TASK_MAPPING.items():
        sec = ", ".join(f"`{s}`" for s in info["secondary"])
        fns = ", ".join(info["key_functions"])
        lines.append(f"| `{task}` | `{info['primary']}` | {sec} | {fns} |")

    lines.append("")

    # ── Topology-driven file index ────────────────────────────────────────────
    if not os.path.exists(topology_path):
        lines.append("## File Index\n")
        lines.append("_Topology file not found. Run `!topology` first, then re-run "
                     "`generate_ai_router.py`._\n")
        lines.append("## Shared Resource Index\n")
        lines.append("_Not available without topology._\n")
        return "\n".join(lines)

    try:
        with open(topology_path, "r", encoding="utf-8") as f:
            topo = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        lines.append(f"\n_Error loading topology: {exc}_\n")
        return "\n".join(lines)

    nodes: List[Dict] = topo.get("nodes", [])
    edges: List[Dict] = topo.get("edges", [])
    node_by_id: Dict[str, Dict] = {n["id"]: n for n in nodes}

    # Group nodes by file
    file_nodes: Dict[str, List[Dict]] = defaultdict(list)
    for n in nodes:
        file = n.get("file") or (n["id"].split("::")[0] if "::" in n["id"] else "unknown")
        file_nodes[file].append(n)

    lines.append("## File Index (PSML headers)\n")

    for file, node_list in sorted(file_nodes.items()):
        header = extract_psml_header(file)

        # Resolve dependency info from topology edges if header is empty
        if not header["dependencies"]:
            dep_set: set = set()
            for e in edges:
                src = e.get("source", "")
                tgt = e.get("target", "")
                src_file = node_by_id.get(src, {}).get("file", "")
                tgt_file = node_by_id.get(tgt, {}).get("file", "")
                if src_file == file and tgt_file and tgt_file != file:
                    dep_set.add(tgt_file)
            header["dependencies"] = sorted(dep_set)[:6]

        # Compute line ranges via AST
        line_ranges = _extract_line_ranges(file, header["primary_functions"])

        lines.append(f"### `{file}`")
        lines.append(f"- **Purpose**: {header['purpose']}")

        if header["dependencies"]:
            dep_str = ", ".join(f"`{d}`" for d in header["dependencies"][:6])
            lines.append(f"- **Dependencies**: {dep_str}")
        else:
            lines.append("- **Dependencies**: _(auto-detected from topology)_")

        if header["primary_functions"]:
            lines.append("- **Primary functions**:")
            for fn in header["primary_functions"]:
                lineno = line_ranges.get(fn)
                suffix = f" _(line {lineno})_" if lineno else ""
                lines.append(f"  - `{fn}(){suffix}`")
        else:
            lines.append("- **Primary functions**: _(none detected)_")

        # Calls detected from explicit function-call edges
        called: set = set()
        for e in edges:
            if (e.get("type") == "explicit_function_call"
                    and node_by_id.get(e.get("source", ""), {}).get("file") == file):
                tgt_label = node_by_id.get(e.get("target", ""), {}).get("label", "")
                if tgt_label:
                    called.add(tgt_label)
        if called:
            calls_str = ", ".join(f"`{c}`" for c in sorted(called)[:6])
            lines.append(f"- **Calls**: {calls_str}")

        lines.append("")

    # ── Shared resource index ─────────────────────────────────────────────────
    resources = _detect_shared_resources(nodes, edges, node_by_id)
    lines.append("## Shared Resource Index\n")
    if resources:
        lines.append("| Resource type | Name | Note |")
        lines.append("|:--------------|:-----|:-----|")
        for rtype, names in resources.items():
            for name in sorted(set(names))[:6]:
                lines.append(f"| {rtype} | `{name}` | from topology |")
    else:
        lines.append("_No shared resources detected in topology._")

    lines.append("")

    # ── Agent usage instructions ──────────────────────────────────────────────
    lines.append("## For AI Agents: How to Use This Router\n")
    lines.append(
        "1. **Find your task** in the *Task → File Mapping* table.\n"
        "2. **Open that file's section** in *File Index* to get purpose, dependencies, "
        "and key functions with exact line numbers.\n"
        "3. **Read only the target function** – not the entire file – to stay within "
        "context limits.\n"
        "4. **Check the Shared Resource Index** before modifying ports, databases, or "
        "memory stores to avoid breaking other modules.\n"
        "5. After generating code, run `!topology` and `!catalyze` to verify "
        "structural integrity.\n"
        "6. Regenerate this file with `python3 generate_ai_router.py` or `!topology deep`.\n"
    )

    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Generate AURA_AI_ROUTER.md from live topology")
    p.add_argument("--topology", default=TOPOLOGY_PATH,
                   help="Path to live_topology_ast.json")
    p.add_argument("--output", default=OUTPUT_MD,
                   help="Output Markdown file path")
    p.add_argument("--quiet", action="store_true")
    args = p.parse_args(argv)

    md = build_router_md(topology_path=args.topology, output_path=args.output)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(md)

    if not args.quiet:
        print(f"[+] Generated {args.output} "
              f"({len(md.splitlines())} lines, {len(md):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
