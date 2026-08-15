from __future__ import annotations

from pathlib import Path

NAV = Path(__file__).resolve().parents[1] / "aura_codebase_navigator.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def main() -> int:
    text = NAV.read_text(encoding="utf-8")
    text = replace_once(
        text,
        '''    if topology is None:
        try:
            topology, _ = load_or_compile_topology(root, refresh=False)
        except (OSError, RuntimeError, ValueError, json.JSONDecodeError):
            topology = None
''',
        '''    if topology is None and legacy_call:
        try:
            topology, _ = load_or_compile_topology(root, refresh=False)
        except (OSError, RuntimeError, ValueError, json.JSONDecodeError):
            topology = None
''',
        "current no-topology refresh must stay topology-free",
    )
    text = replace_once(
        text,
        '''    canonical.pop("incremental_refresh", None)
    raw = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
''',
        '''    canonical.pop("incremental_refresh", None)
    canonical.pop("last_refresh", None)
    raw = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
''',
        "legacy refresh projection is non-semantic",
    )
    NAV.write_text(text, encoding="utf-8")
    print("WC-02 Phase4 navigator composition repair applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
