from __future__ import annotations

from pathlib import Path


def replace_required(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"missing semantic detector target: {label}")
    return text.replace(old, new, 1)


def main() -> None:
    path = Path("aura_waboose_semantic_rules.py")
    text = path.read_text(encoding="utf-8")
    text = replace_required(
        text,
        '''        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = _function_text(lines, node)
''',
        '''        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name.startswith("test_"):
            # Regression fixtures often embed intentionally broken source strings.
            # Analyze the embedded source when the test calls the public scanner,
            # not the test function's surrounding text as production logic.
            continue
        body = _function_text(lines, node)
''',
        "skip embedded test fixtures",
    )
    text = replace_required(
        text,
        '''        endpoint_filter = (
            "edge.src_id in selected" in compact
            and "edge.dst_id in selected" in compact
        )
''',
        '''        endpoint_filter = (
            (
                "edge.src_id in selected" in compact
                and "edge.dst_id in selected" in compact
            )
            or (
                "edge.src_id not in selected" in compact
                and "edge.dst_id not in selected" in compact
            )
        )
''',
        "recognize negative endpoint guard",
    )
    text = replace_required(
        text,
        '''        preserves_test_sources = (
            'edge.edge_type == "test"' in compact
            and "include_ids.add(edge.src_id)" in compact
        )
''',
        '''        preserves_test_sources = (
            (
                'edge.edge_type == "test"' in compact
                and "include_ids.add(edge.src_id)" in compact
            )
            or (
                "node.file_path in tests" in compact
                and "node.kind in ATOMIC_KINDS" in compact
                and "include_ids.add(node.node_id)" in compact
            )
        )
''',
        "recognize atomic test callable admission",
    )
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
