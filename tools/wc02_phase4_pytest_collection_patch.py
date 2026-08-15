from __future__ import annotations

from pathlib import Path


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> int:
    replace_once(
        Path("test_aura_functions.py"),
        "sys.exit(0 if fails == 0 else 1)\n",
        "if __name__ == \"__main__\":\n"
        "    raise SystemExit(0 if fails == 0 else 1)\n"
        "if fails:\n"
        "    raise AssertionError(f\"{fails} legacy Aura function checks failed\")\n",
        "Aura function harness exit boundary",
    )

    replace_once(
        Path("test_synthesis_upgrades.py"),
        "sys.exit(0 if fails == 0 else 1)\n",
        "if __name__ == \"__main__\":\n"
        "    raise SystemExit(0 if fails == 0 else 1)\n"
        "if fails:\n"
        "    raise AssertionError(f\"{fails} synthesis upgrade checks failed\")\n",
        "Synthesis harness exit boundary",
    )

    replace_once(
        Path("test_syntax_fixes.py"),
        "if all_passed:\n"
        "    print(\"\\n✅ All syntax fixes validated!\")\n"
        "    sys.exit(0)\n"
        "else:\n"
        "    print(\"\\n❌ Some files still have syntax errors\")\n"
        "    sys.exit(1)\n",
        "if all_passed:\n"
        "    print(\"\\n✅ All syntax fixes validated!\")\n"
        "else:\n"
        "    print(\"\\n❌ Some files still have syntax errors\")\n"
        "\n"
        "if __name__ == \"__main__\":\n"
        "    raise SystemExit(0 if all_passed else 1)\n"
        "if not all_passed:\n"
        "    raise AssertionError(\"legacy syntax validation failed\")\n",
        "Syntax harness exit boundary",
    )

    print("WC-02 Phase4 pytest collection boundaries applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
