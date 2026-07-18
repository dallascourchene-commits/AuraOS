from __future__ import annotations

from pathlib import Path


def main() -> None:
    path = Path("scripts/apply_waboose_coderabbit_learning.py")
    text = path.read_text(encoding="utf-8")
    old = '''# Public request alias.
'''
    new = '''# Public request alias.  The underlying generic review request remains reusable.
'''
    occurrences = text.count(old)
    if occurrences != 2:
        raise SystemExit(
            f"expected two Waboose public-alias patch markers, found {occurrences}"
        )
    path.write_text(text.replace(old, new), encoding="utf-8")


if __name__ == "__main__":
    main()
