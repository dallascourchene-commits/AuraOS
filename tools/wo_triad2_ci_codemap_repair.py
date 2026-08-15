from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAV = ROOT / "aura_codebase_navigator.py"
VERIFY = ROOT / "aura_codemap_verify.py"
CI = ROOT / ".github/workflows/ci.yml"
STALE = ROOT / ".github/workflows/unified-memory-continuity-deep-v2-target.yml"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one anchor, found {count}")
    return text.replace(old, new, 1)


def replace_region(text: str, start_marker: str, end_marker: str, replacement: str, label: str) -> str:
    start = text.find(start_marker)
    if start < 0:
        raise RuntimeError(f"{label}: start marker missing")
    end = text.find(end_marker, start)
    if end < 0:
        raise RuntimeError(f"{label}: end marker missing")
    return text[:start] + replacement.rstrip() + "\n\n" + text[end:]


def patch_navigator() -> None:
    text = NAV.read_text(encoding="utf-8")

    load_fn = '''def load_or_compile_topology(
    root: Path,
    *,
    topology_path: Path | None = None,
    refresh: bool = False,
) -> tuple[dict[str, Any], str]:
    target = topology_path or DEFAULT_TOPOLOGY_PATH
    absolute = target if target.is_absolute() else root / target
    if absolute.exists() and not refresh:
        try:
            return json.loads(absolute.read_text(encoding="utf-8")), "existing"
        except (OSError, json.JSONDecodeError):
            pass

    # The deep compiler currently binds its scan root and output paths to the
    # process working directory. Run it from the requested repository root, then
    # restore the caller's cwd so library use remains side-effect bounded.
    previous_cwd = Path.cwd()
    try:
        os.chdir(root)
        topology = compile_topology_map(deep=True)
    finally:
        os.chdir(previous_cwd)

    generated_by = str((topology.get("meta") or {}).get("generated_by") or "")
    source = "compiled_deep_topology" if generated_by == "aura_topology_manager" else "compiled_standard_topology"
    return topology, source
'''
    text = replace_region(text, "def load_or_compile_topology(\n", "def _node_file(", load_fn, "load_or_compile_topology")

    index_fn = '''def _topology_file_index(topology: dict[str, Any]) -> dict[str, dict[str, Any]]:
    per_file: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "node_count": 0,
        "edge_count": 0,
        "degree": 0,
        "out_edges": 0,
        "in_edges": 0,
        "edge_kinds": Counter(),
        "kinds": Counter(),
        "symbols": [],
        "neighbor_files": set(),
    })

    raw_nodes = topology.get("nodes", {})
    if isinstance(raw_nodes, dict):
        node_items = raw_nodes.items()
    elif isinstance(raw_nodes, list):
        node_items = (
            (str(node.get("id") or f"node_{index}"), node)
            for index, node in enumerate(raw_nodes)
            if isinstance(node, dict)
        )
    else:
        node_items = []

    node_to_file: dict[str, str] = {}
    for node_id, node in node_items:
        if not isinstance(node, dict):
            continue
        file_path = _node_file(str(node_id), node)
        if not file_path:
            continue
        node_to_file[str(node_id)] = file_path
        slot = per_file[file_path]
        slot["node_count"] += 1
        slot["kinds"][str(node.get("kind", "unknown"))] += 1
        symbol = str(node.get("symbol") or node.get("label") or "")
        if symbol and symbol != "global_scope" and len(slot["symbols"]) < 12 and symbol not in slot["symbols"]:
            slot["symbols"].append(symbol)

    for edge in topology.get("edges", []) or []:
        if not isinstance(edge, dict):
            continue
        source_id = str(edge.get("source") or edge.get("from") or "")
        target_id = str(edge.get("target") or edge.get("to") or "")
        source_file = node_to_file.get(source_id)
        target_file = node_to_file.get(target_id)
        edge_kind = str(edge.get("kind") or edge.get("type") or "unknown")
        if source_file:
            slot = per_file[source_file]
            slot["out_edges"] += 1
            slot["edge_count"] += 1
            slot["degree"] += 1
            slot["edge_kinds"][edge_kind] += 1
            if target_file and target_file != source_file:
                slot["neighbor_files"].add(target_file)
        if target_file:
            slot = per_file[target_file]
            slot["in_edges"] += 1
            slot["edge_count"] += 1
            slot["degree"] += 1
            slot["edge_kinds"][edge_kind] += 1
            if source_file and source_file != target_file:
                slot["neighbor_files"].add(source_file)

    out: dict[str, dict[str, Any]] = {}
    for file_path, payload in per_file.items():
        out[file_path] = {
            "node_count": int(payload["node_count"]),
            "edge_count": int(payload["edge_count"]),
            "degree": int(payload["degree"]),
            "symbols": list(payload["symbols"]),
            "neighbor_files": sorted(payload["neighbor_files"]),
            "edge_kinds": dict(sorted(payload["edge_kinds"].items())),
            # Compatibility fields consumed by the navigation ranking layer.
            "nodes": int(payload["node_count"]),
            "out_edges": int(payload["out_edges"]),
            "in_edges": int(payload["in_edges"]),
            "kinds": dict(sorted(payload["kinds"].items())),
        }
    return out
'''
    text = replace_region(text, "def _topology_file_index(", "def scan_repository(", index_fn, "_topology_file_index")

    text = replace_once(
        text,
        '        "tokens_est": estimate_tokens(text) if not is_binary else max(1, len(raw) // 4),\n        "symbols": [record.__dict__ for record in symbols],',
        '        "tokens_est": estimate_tokens(text) if not is_binary else max(1, len(raw) // 4),\n        "binary": is_binary,\n        "symbols": [record.__dict__ for record in symbols],',
        "binary scan metadata",
    )
    text = replace_once(
        text,
        '            "tokens_est": card["tokens_est"],\n            "symbol_count": len(card.get("symbols", [])),',
        '            "tokens_est": card["tokens_est"],\n            "binary": bool(card.get("binary", False)),\n            "symbol_count": len(card.get("symbols", [])),',
        "binary compact metadata",
    )

    old_topology_setup = '''    topology: dict[str, Any] | None = None
    topology_source = "disabled"
    if include_topology:
        topology, topology_source = load_or_compile_topology(root, topology_path=topology_path, refresh=refresh_topology)
        cards = _attach_topology(cards, _topology_file_index(topology))
    payload = {'''
    new_topology_setup = '''    topology: dict[str, Any] | None = None
    topology_source = "disabled"
    topology_index: dict[str, dict[str, Any]] = {}
    if include_topology:
        topology, topology_source = load_or_compile_topology(root, topology_path=topology_path, refresh=refresh_topology)
        topology_index = _topology_file_index(topology)
        cards = _attach_topology(cards, topology_index)
    payload = {'''
    text = replace_once(text, old_topology_setup, new_topology_setup, "build topology setup")

    text = replace_once(
        text,
        '        "files": _compact_file_cards(cards),\n        "summary": {',
        '        "files": _compact_file_cards(cards),\n        "topology": {\n            "source": topology_source,\n            "file_index": topology_index,\n            "meta": dict((topology or {}).get("meta") or {}),\n            "diagnostics": dict((topology or {}).get("diagnostics") or {}),\n        },\n        "summary": {',
        "top-level topology contract",
    )

    NAV.write_text(text, encoding="utf-8")


def patch_verifier() -> None:
    text = VERIFY.read_text(encoding="utf-8")
    text = replace_once(
        text,
        '    "tokens_est",\n    "symbol_count",',
        '    "tokens_est",\n    "binary",\n    "symbol_count",',
        "stable binary source-card field",
    )
    VERIFY.write_text(text, encoding="utf-8")


def patch_ci() -> None:
    text = CI.read_text(encoding="utf-8")
    needle = "python aura_codebase_navigator.py"
    count = text.count(needle)
    if count != 2:
        raise RuntimeError(f"ci deep regeneration anchors: expected 2, found {count}")
    text = text.replace(needle, "python aura_codebase_navigator.py --refresh-topology")
    CI.write_text(text, encoding="utf-8")


def retire_stale_target() -> None:
    if not STALE.exists():
        raise RuntimeError("stale PR #193 target workflow is unexpectedly absent")
    STALE.unlink()


def main() -> int:
    patch_navigator()
    patch_verifier()
    patch_ci()
    retire_stale_target()
    print("WO-TRIAD2-CI-CODEMAP-REPAIR-001 source transform applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
