from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "aura_architect_loop.py"

OLD = '''def _refresh_plan_codemap_targets(plan: FractalPlanCapsule, repo_root: str | Path) -> None:
    targets = sorted({
        normalized
        for normalized in (_normalize_path(act.target_file) for act in plan.act_capsules)
        if normalized
    })
    if not targets:
        return
    try:
        refresh_codemap_for_paths(targets, root=Path(repo_root), include_topology=True)
    except Exception as exc:
        _LOG.debug("CODEMAP target preflight refresh skipped: %s", type(exc).__name__)
        return
'''

NEW = '''def _refresh_plan_codemap_targets(plan: FractalPlanCapsule, repo_root: str | Path) -> None:
    root = Path(repo_root)
    # Grounding is fail-closed on CODEMAP absence. Refresh may update a known
    # navigation artifact, but it must never manufacture the artifact that is
    # itself the prerequisite for grounding.
    if not (root / ".aura" / "CODEMAP.json").is_file():
        return
    targets = sorted({
        normalized
        for normalized in (_normalize_path(act.target_file) for act in plan.act_capsules)
        if normalized
    })
    if not targets:
        return
    try:
        refresh_codemap_for_paths(targets, root=root, include_topology=True)
    except Exception as exc:
        _LOG.debug("CODEMAP target preflight refresh skipped: %s", type(exc).__name__)
        return
'''


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    count = text.count(OLD)
    if count != 1:
        raise RuntimeError(f"Architect fail-closed refresh anchor expected once, found {count}")
    TARGET.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    Path(__file__).unlink()
    print("Architect CODEMAP absence remains fail-closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
