from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "aura_agent_arena_bridge.py"

OLD = '''        coverage = codemap.get("coverage", {})
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
'''

NEW = '''        summary = codemap.get("summary", {})
        files = codemap.get("files", [])
        coverage = codemap.get("coverage", {})

        file_count = 0
        if isinstance(summary, dict):
            file_count = int(summary.get("file_count", 0) or 0)
        if not file_count and isinstance(files, list):
            file_count = len(files)
        if not file_count and isinstance(coverage, dict):
            file_count = int(coverage.get("included_file_count", 0) or 0)
            all_paths = coverage.get("all_included_paths_sorted", []) or []
            if not file_count and isinstance(all_paths, list):
                file_count = len(all_paths)

        symbol_index = codemap.get("symbol_index", {})
        topology = codemap.get("topology", {})
        topology_nodes = 0
        topology_edges = 0
        if isinstance(summary, dict):
            topology_nodes = int(summary.get("topology_nodes", 0) or 0)
            topology_edges = int(summary.get("topology_edges", 0) or 0)
        if not topology_nodes and isinstance(topology, dict):
            topology_nodes = len(topology.get("nodes", []) or [])
        if not topology_edges and isinstance(topology, dict):
            topology_edges = len(topology.get("edges", []) or [])
        if not topology_nodes and isinstance(topology, list):
            topology_nodes = len(topology)
'''


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    count = text.count(OLD)
    if count != 1:
        raise RuntimeError(f"Agent Arena CODEMAP digest anchor expected once, found {count}")
    TARGET.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    Path(__file__).unlink()
    print("Agent Arena bridge digest now reads canonical CODEMAP summary/files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
