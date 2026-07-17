"""Normalize trailing whitespace in the two final canonical documentation anchors."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
for relative in (".aura/ARCHITECTURE.md", "USER_GUIDE.md"):
    path = root / relative
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text("\n".join(line.rstrip() for line in lines) + "\n", encoding="utf-8")
