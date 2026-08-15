from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "aura_topology_health.py"

OLD = '''    cm = _load_codemap(root)\n    coverage = cm.get("coverage", {})\n    file_count = int(coverage.get("included_file_count", 0))\n    topo = cm.get("topology", {})\n    summary = cm.get("summary", {})\n'''
NEW = '''    cm = _load_codemap(root)\n    coverage = cm.get("coverage", {})\n    topo = cm.get("topology", {})\n    summary = cm.get("summary", {})\n    files = cm.get("files", [])\n    # CODEMAP V4 keeps the canonical count in summary.file_count and the full\n    # scanned repository count in coverage.repo_file_count. Older generations\n    # used coverage.included_file_count. Accept all three without inventing a\n    # count, preferring the current canonical summary.\n    file_count = int(\n        summary.get("file_count")\n        or coverage.get("included_file_count")\n        or coverage.get("repo_file_count")\n        or (len(files) if isinstance(files, list) else 0)\n    )\n'''


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    if NEW in text:
        print("WC-02 topology-health CODEMAP schema compatibility already applied")
        return 0
    count = text.count(OLD)
    if count != 1:
        raise RuntimeError(f"topology-health schema anchor expected once, found {count}")
    TARGET.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    print("WC-02 topology-health CODEMAP V4 schema compatibility applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
