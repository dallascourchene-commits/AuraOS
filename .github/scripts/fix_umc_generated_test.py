from __future__ import annotations

from pathlib import Path


def ensure_import(path: str, *, anchor: str, import_line: str) -> None:
    file = Path(path)
    text = file.read_text(encoding="utf-8")
    if import_line in text:
        return
    if text.count(anchor) != 1:
        raise SystemExit(f"{path}: import anchor is not unique")
    file.write_text(text.replace(anchor, f"{anchor}{import_line}", 1), encoding="utf-8")


ensure_import(
    "tests/test_aura_unified_memory_continuity.py",
    anchor="from dataclasses import replace\nimport math\n",
    import_line="from pathlib import Path\n",
)
ensure_import(
    "aura_agent_arena_bridge.py",
    anchor="from __future__ import annotations\n\n",
    import_line="from collections.abc import Mapping\n",
)

print("Unified memory generated imports are complete.")
