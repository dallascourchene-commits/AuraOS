"""Apply verified exact cleanups before the final Construction audit."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]

plan_path = root / "aura_construction_refactor_plan.py"
text = plan_path.read_text(encoding="utf-8")
old = "    SourceSpan,\n"
if old in text:
    if text.count(old) != 1:
        raise RuntimeError("expected one SourceSpan import")
    text = text.replace(old, "", 1)
plan_path.write_text(text, encoding="utf-8")

test_cleanup = root / "tools" / "apply_sco_completion_test_cleanup.py"
if test_cleanup.exists():
    namespace = {"__file__": str(test_cleanup), "__name__": "__main__"}
    exec(
        compile(test_cleanup.read_text(encoding="utf-8"), str(test_cleanup), "exec"),
        namespace,
    )
    test_cleanup.unlink()
