"""Remove the verified-unused historical SourceSpan import exposed by fatal Ruff."""
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "aura_construction_refactor_plan.py"
text = path.read_text(encoding="utf-8")
old = "    SourceSpan,\n"
if old in text:
    if text.count(old) != 1:
        raise RuntimeError("expected one SourceSpan import")
    text = text.replace(old, "", 1)
path.write_text(text, encoding="utf-8")
