#!/usr/bin/env python3
"""Independent stdlib-AST oracle for the ASTGE module-symbol V1 fixture."""

from __future__ import annotations

import ast
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "crates" / "aura-k27-astge-symbols" / "fixtures" / "python_module_symbols.py"


def main() -> int:
    source = FIXTURE.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(FIXTURE))
    rows: list[tuple[str, str]] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            rows.append(("FUNCTION", node.name))
        elif isinstance(node, ast.ClassDef):
            rows.append(("CLASS", node.name))
    for ordinal, (kind, name) in enumerate(rows):
        print(f"{ordinal}|{kind}|{name}")
    counts = Counter(name for _, name in rows)
    duplicates = sorted(name for name, count in counts.items() if count > 1)
    print("DUP|" + ",".join(duplicates))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
