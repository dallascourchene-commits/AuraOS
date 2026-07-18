from __future__ import annotations

from pathlib import Path


def replace_required(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"missing learning follow-up target: {label}")
    return text.replace(old, new, 1)


def patch_learning() -> None:
    path = Path("aura_waboose_learning.py")
    text = path.read_text(encoding="utf-8")
    text = replace_required(
        text,
        '''def _tokens(value: Any) -> set[str]:
    return {item.lower() for item in _TOKEN_RE.findall(str(value or ""))}


def _safe_repo_path''',
        '''def _tokens(value: Any) -> set[str]:
    return {item.lower() for item in _TOKEN_RE.findall(str(value or ""))}


def _strict_boolean(value: Any, *, default: bool, field_name: str) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise ValueError(f"{field_name} must be a boolean")


def _safe_repo_path''',
        "strict learning boolean helper",
    )
    text = replace_required(
        text,
        '''        path = dict(resolution.get("capability_connectome_path") or {})
        return {
            "ok": bool(path.get("ok", True)),
''',
        '''        path = dict(resolution.get("capability_connectome_path") or {})
        path_ok = _strict_boolean(
            path.get("ok"),
            default=True,
            field_name="capability_connectome_path.ok",
        )
        return {
            "ok": path_ok,
''',
        "strict Connectome status",
    )
    text = replace_required(
        text,
        '''            "title_tokens": sorted(_tokens(f"{lesson.title} {lesson.message}"))[:160],
''',
        '''            "title_tokens": sorted(
                _tokens(
                    f"{lesson.title} {lesson.message} {lesson.source_excerpt}"
                )
            )[:160],
''',
        "DREAM source excerpt features",
    )
    path.write_text(text, encoding="utf-8")


def patch_emergent_test_evidence() -> None:
    path = Path("aura_emergent_evidence_spine.py")
    text = path.read_text(encoding="utf-8")
    text = replace_required(
        text,
        '''    selected_module_ids.discard(None)
    test_targets = include_ids | selected_module_ids
    for edge in anchor.edges:
''',
        '''    selected_module_ids.discard(None)
    for node in anchor.nodes.values():
        if node.file_path in tests and node.kind in ATOMIC_KINDS:
            include_ids.add(node.node_id)
    test_targets = include_ids | selected_module_ids
    for edge in anchor.edges:
''',
        "atomic test callable preservation",
    )
    path.write_text(text, encoding="utf-8")


def main() -> None:
    patch_learning()
    patch_emergent_test_evidence()


if __name__ == "__main__":
    main()
