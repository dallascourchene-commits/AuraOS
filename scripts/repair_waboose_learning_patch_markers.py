from __future__ import annotations

from pathlib import Path


def replace_exact_count(
    text: str,
    old: str,
    new: str,
    *,
    expected: int,
    label: str,
) -> str:
    occurrences = text.count(old)
    if occurrences != expected:
        raise SystemExit(
            f"expected {expected} {label} markers, found {occurrences}"
        )
    return text.replace(old, new)


def main() -> None:
    path = Path("scripts/apply_waboose_coderabbit_learning.py")
    text = path.read_text(encoding="utf-8")
    text = replace_exact_count(
        text,
        '''# Public request alias.
''',
        '''# Public request alias.  The underlying generic review request remains reusable.
''',
        expected=2,
        label="Waboose public-alias",
    )
    text = replace_exact_count(
        text,
        '''    marker = '''\'''    def aura_waboose_prepare(
'''\'''
''',
        '''    marker = '''\'''    def aura_waboose_prepare(self, request: Mapping[str, Any]) -> dict[str, Any]:
'''\'''
''',
        expected=1,
        label="Agent Bridge learning method",
    )
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
