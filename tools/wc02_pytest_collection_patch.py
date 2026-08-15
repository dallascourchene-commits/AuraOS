from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PATCHES = {
    "test_aura_functions.py": (
        "sys.exit(0 if fails == 0 else 1)",
        'if __name__ == "__main__":\n    sys.exit(0 if fails == 0 else 1)',
    ),
    "test_synthesis_upgrades.py": (
        "sys.exit(0 if fails == 0 else 1)",
        'if __name__ == "__main__":\n    sys.exit(0 if fails == 0 else 1)',
    ),
}


def _patch_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path.name}: expected one collection-exit anchor, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def _patch_syntax_script(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    old_ok = '    sys.exit(0)\nelse:\n'
    new_ok = '    if __name__ == "__main__":\n        sys.exit(0)\nelse:\n'
    old_fail = '    sys.exit(1)\n\n# Made with Bob'
    new_fail = '    if __name__ == "__main__":\n        sys.exit(1)\n\n# Made with Bob'
    if new_ok not in text:
        if text.count(old_ok) != 1:
            raise RuntimeError("test_syntax_fixes.py: success-exit anchor mismatch")
        text = text.replace(old_ok, new_ok, 1)
    if new_fail not in text:
        if text.count(old_fail) != 1:
            raise RuntimeError("test_syntax_fixes.py: failure-exit anchor mismatch")
        text = text.replace(old_fail, new_fail, 1)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    for name, (old, new) in PATCHES.items():
        _patch_once(ROOT / name, old, new)
    _patch_syntax_script(ROOT / "test_syntax_fixes.py")
    print("WC-02 pytest collection exits normalized; standalone exit semantics preserved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
