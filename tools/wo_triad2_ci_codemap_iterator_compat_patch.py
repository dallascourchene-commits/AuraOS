from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "aura_codebase_navigator.py"
OLD = 'def _iter_repo_files(root: Path, *, skip_dirs: frozenset[str] = DEFAULT_SKIP_DIRS) -> list[Path]:'
NEW = 'def _iter_repo_files(root: Path, skip_dirs: frozenset[str] = DEFAULT_SKIP_DIRS) -> list[Path]:'

def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    count = text.count(OLD)
    if count != 1:
        raise RuntimeError(f"iterator compatibility anchor expected once, found {count}")
    TARGET.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    Path(__file__).unlink()
    print("CODEMAP iterator positional skip_dirs compatibility restored")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
