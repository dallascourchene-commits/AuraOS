"""Remove the one-time documentation sync hook before CODEMAP regeneration."""
from __future__ import annotations

from pathlib import Path

START = "      # AURA_DOC_SYNC_START\n"
END = "      # AURA_DOC_SYNC_END\n"


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    workflow = root / ".github" / "workflows" / "architect-code-quality-benchmark.yml"
    text = workflow.read_text(encoding="utf-8")
    if START in text and END in text:
        before, rest = text.split(START, 1)
        _temporary, after = rest.split(END, 1)
        text = before + after
    text = text.replace("permissions:\n  contents: write", "permissions:\n  contents: read", 1)
    workflow.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
