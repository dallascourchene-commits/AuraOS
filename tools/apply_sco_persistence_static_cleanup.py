"""Remove two verified-unused imports exposed by the Phase 4 fatal Ruff gate."""
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "aura_coding_workbench_wfst_adapter.py"
text = path.read_text(encoding="utf-8")
replacements = {
    "from typing import Any, Callable\n": "from typing import Any\n",
    "from aura_coding_workbench_sequence import GATE_DEFINITIONS, WorkbenchState, get_gate\n": (
        "from aura_coding_workbench_sequence import WorkbenchState, get_gate\n"
    ),
}
for old, new in replacements.items():
    if new in text:
        continue
    if text.count(old) != 1:
        raise RuntimeError(f"expected one static-cleanup anchor: {old!r}")
    text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")
