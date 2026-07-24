from __future__ import annotations

from pathlib import Path


path = Path("tests/test_aura_unified_memory_continuity.py")
text = path.read_text(encoding="utf-8")
import_line = "from pathlib import Path\n"
if import_line not in text:
    anchor = "from dataclasses import replace\nimport math\n"
    if text.count(anchor) != 1:
        raise SystemExit("test import anchor is not unique")
    text = text.replace(anchor, f"{anchor}{import_line}", 1)
    path.write_text(text, encoding="utf-8")

print("Unified memory test imports are complete.")
