from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "aura_codebase_navigator.py"

ANCHOR = '''def _iter_repo_files(root: Path, *, skip_dirs: frozenset[str] = DEFAULT_SKIP_DIRS) -> list[Path]:
    files: list[Path] = []
    for base, dirs, names in os.walk(root):
        dirs[:] = [name for name in dirs if name not in skip_dirs and not name.endswith(".egg-info")]
        base_path = Path(base)
        for name in names:
            path = base_path / name
            rel = path.relative_to(root).as_posix()
            if rel in GENERATED_MAP_FILES or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            files.append(path)
    return sorted(files)
'''

REPLACEMENT = '''def _iter_repo_files(root: Path, skip_dirs: frozenset[str] = DEFAULT_SKIP_DIRS) -> list[Path]:
    """Return source files while preserving the historical positional skip_dirs API."""
    files: list[Path] = []
    for base, dirs, names in os.walk(root):
        dirs[:] = [name for name in dirs if name not in skip_dirs and not name.endswith(".egg-info")]
        base_path = Path(base)
        for name in names:
            path = base_path / name
            rel = path.relative_to(root).as_posix()
            if rel in GENERATED_MAP_FILES or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            files.append(path)
    return sorted(files)
'''

COMPAT_SIGNATURE = "def _iter_repo_files(root: Path, skip_dirs: frozenset[str] = DEFAULT_SKIP_DIRS) -> list[Path]:"


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    # Another fleet transform may have already restored the same compatibility
    # surface. Treat equivalent convergence as NOOP rather than a collision.
    if COMPAT_SIGNATURE in text:
        print("Phase-3 CODEMAP file-walker positional compatibility already satisfied")
        return 0
    count = text.count(ANCHOR)
    if count != 1:
        raise RuntimeError(f"CODEMAP file-walker compatibility anchor expected once, found {count}")
    TARGET.write_text(text.replace(ANCHOR, REPLACEMENT, 1), encoding="utf-8")
    print("Phase-3 CODEMAP file-walker positional compatibility repair applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
