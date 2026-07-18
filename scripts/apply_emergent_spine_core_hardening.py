from __future__ import annotations

from pathlib import Path


def main() -> None:
    path = Path("aura_emergent_evidence_spine.py")
    text = path.read_text(encoding="utf-8")
    old = '''def _repo_paths(values: Any) -> tuple[str, ...]:
    result: list[str] = []
    for value in _sequence(values):
        normalized = _normalize_repo_path(value)
        if normalized and normalized not in result:
            result.append(normalized)
    return tuple(result)
'''
    new = '''def _repo_paths(values: Any) -> tuple[str, ...]:
    result: list[str] = []
    for value in _sequence(values):
        raw = str(value or "").strip()
        normalized = _normalize_repo_path(value)
        if raw and not normalized:
            raise ValueError("repository paths must be relative and may not escape the repository")
        if normalized and normalized not in result:
            result.append(normalized)
    return tuple(result)
'''
    if old not in text:
        raise SystemExit("core path-hardening target not found")
    path.write_text(text.replace(old, new), encoding="utf-8")


if __name__ == "__main__":
    main()
