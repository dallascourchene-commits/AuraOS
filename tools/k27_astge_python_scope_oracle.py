#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import subprocess
import symtable
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "crates" / "aura-k27-astge-scopes" / "fixtures" / "python_nested_scopes.py"
MANIFEST = ROOT / "crates" / "aura-k27-astge-scopes" / "Cargo.toml"


def normalized_type(table: symtable.SymbolTable) -> str:
    value = table.get_type()
    if hasattr(value, "value"):
        value = value.value
    text = str(value).upper()
    mapping = {
        "MODULE": "MODULE",
        "FUNCTION": "FUNCTION",
        "CLASS": "CLASS",
    }
    if text not in mapping:
        raise RuntimeError(f"unsupported symtable scope type: {text}")
    return mapping[text]


def cpython_rows(source: str) -> list[tuple[int, int | None, str, str, int]]:
    root = symtable.symtable(source, str(FIXTURE), "exec")
    out: list[tuple[int, int | None, str, str, int]] = []

    def walk(table: symtable.SymbolTable, parent: int | None) -> None:
        scope_id = len(out)
        kind = normalized_type(table)
        name = "<module>" if kind == "MODULE" else table.get_name()
        line = 0 if kind == "MODULE" else int(table.get_lineno())
        out.append((scope_id, parent, kind, name, line))
        for child in table.get_children():
            walk(child, scope_id)

    walk(root, None)
    return out


def rust_rows() -> list[tuple[int, int | None, str, str, int]]:
    proc = subprocess.run(
        [
            "cargo",
            "run",
            "--quiet",
            "--manifest-path",
            str(MANIFEST),
            "--example",
            "scope_fixture",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    rows: list[tuple[int, int | None, str, str, int]] = []
    for raw in proc.stdout.splitlines():
        parts = raw.split("\t")
        if len(parts) != 5:
            raise RuntimeError(f"malformed Rust scope row: {raw!r}")
        scope_id_s, parent_s, kind, name, line_s = parts
        parent = None if parent_s == "-" else int(parent_s)
        rows.append((int(scope_id_s), parent, kind, name, int(line_s)))
    return rows


def main() -> int:
    source = FIXTURE.read_text(encoding="utf-8")
    expected = cpython_rows(source)
    observed = rust_rows()
    if observed != expected:
        print("CPYTHON_SYMTABLE_SCOPE_TREE_CONFORMANT=false")
        print("EXPECTED:")
        for row in expected:
            print(row)
        print("OBSERVED:")
        for row in observed:
            print(row)
        return 1
    print("CPYTHON_SYMTABLE_SCOPE_TREE_CONFORMANT=true")
    print(f"SCOPE_COUNT={len(observed)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
