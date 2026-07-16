"""Install measured refactor-quality fragments into canonical Aura documents."""
from __future__ import annotations

from pathlib import Path

START = "<!-- AURA_REFACTOR_CODE_QUALITY:START -->"
END = "<!-- AURA_REFACTOR_CODE_QUALITY:END -->"


def marked(fragment: str) -> str:
    return f"{START}\n{fragment.strip()}\n{END}"


def replace_or_insert(text: str, fragment: str, anchor: str) -> str:
    block = marked(fragment)
    if START in text and END in text:
        before, rest = text.split(START, 1)
        _old, after = rest.split(END, 1)
        return before + block + after
    if anchor not in text:
        raise RuntimeError(f"anchor missing: {anchor}")
    return text.replace(anchor, block + "\n\n" + anchor, 1)


def add_contents(text: str, item: str, anchor: str) -> str:
    if item in text:
        return text
    if anchor not in text:
        raise RuntimeError(f"contents anchor missing: {anchor}")
    return text.replace(anchor, item + "\n" + anchor, 1)


def install(root: Path) -> None:
    fragments = root / "docs" / "fragments"

    readme_path = root / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    readme = replace_or_insert(
        readme,
        (fragments / "README_REFACTOR_CODE_QUALITY.md").read_text(encoding="utf-8"),
        "## Council–Surgeon Hybrid Benchmark",
    )
    readme = add_contents(
        readme,
        "- [Executable Refactor Code Quality](#executable-refactor-code-quality)",
        "- [Council–Surgeon Hybrid Benchmark](#councilsurgeon-hybrid-benchmark)",
    )
    readme_path.write_text(readme, encoding="utf-8")

    architecture_path = root / ".aura" / "ARCHITECTURE.md"
    architecture = architecture_path.read_text(encoding="utf-8")
    architecture = architecture.replace(
        "**Architecture audit:** June 14–July 14, 2026 (through draft PR #92)",
        "**Architecture audit:** June 14–July 16, 2026 (through draft PR #131)",
    )
    architecture = architecture.replace(
        "**CODEMAP state:** 804 indexed files · 7,019 topology nodes · 14,526 topology edges",
        "**CODEMAP state:** generated from the current tree; rerun `python aura_codebase_navigator.py` after architecture changes",
    )
    architecture = replace_or_insert(
        architecture,
        (fragments / "ARCHITECTURE_REFACTOR_CODE_QUALITY.md").read_text(encoding="utf-8"),
        "## 2. Truth and Authority Model",
    )
    architecture_path.write_text(architecture, encoding="utf-8")

    guide_path = root / "USER_GUIDE.md"
    guide = guide_path.read_text(encoding="utf-8")
    guide = guide.replace(
        "**Operator documentation audit:** June 14–July 14, 2026 (through draft PR #92)",
        "**Operator documentation audit:** June 14–July 16, 2026 (through draft PR #131)",
    )
    guide = guide.replace(
        "**Validated CODEMAP:** 804 indexed files · 7,019 topology nodes · 14,526 topology edges · `compiled_deep_topology`",
        "**Validated CODEMAP:** regenerate from the current tree with `python aura_codebase_navigator.py`; require non-zero indexes and `compiled_deep_topology`",
    )
    guide = replace_or_insert(
        guide,
        (fragments / "USER_GUIDE_REFACTOR_CODE_QUALITY.md").read_text(encoding="utf-8"),
        "## 5. Repository Orientation",
    )
    guide = add_contents(
        guide,
        "4A. [Refactor Code-Quality Benchmarking](#4a-refactor-code-quality-benchmarking)",
        "5. [Repository Orientation](#5-repository-orientation)",
    )
    guide_path.write_text(guide, encoding="utf-8")


def main() -> int:
    install(Path(__file__).resolve().parents[1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
