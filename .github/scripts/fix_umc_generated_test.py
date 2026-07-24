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


def replace_exact(path: str, old: str, new: str) -> None:
    file = Path(path)
    text = file.read_text(encoding="utf-8")
    if old not in text:
        return
    if text.count(old) != 1:
        raise SystemExit(f"{path}: cleanup anchor is not unique")
    file.write_text(text.replace(old, new, 1), encoding="utf-8")


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
replace_exact(
    "aura_unified_memory_continuity_toolchain.py",
    "result = subprocess.run(  # noqa: S603",
    "result = subprocess.run(",
)
replace_exact(
    "aura_unified_memory_continuity_toolchain.py",
    '["git", *args],  # noqa: S607',
    '["git", *args],',
)
replace_exact(
    "aura_unified_memory_continuity_toolchain.py",
    "session = bridge._require_session(phase_hash)  # noqa: SLF001 - canonical Bridge lookup",
    "session = bridge._require_session(phase_hash)",
)

print("Unified memory generated imports and lint cleanup are complete.")
