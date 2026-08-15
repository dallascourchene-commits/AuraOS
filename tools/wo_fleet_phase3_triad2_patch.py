from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHITECT = ROOT / "aura_architect_loop.py"
NAV = ROOT / "aura_codebase_navigator.py"
UMC = ROOT / ".github/workflows/unified-memory-continuity-deep-v2-target.yml"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def patch_architect() -> None:
    text = ARCHITECT.read_text(encoding="utf-8")
    old = '''def _refresh_plan_codemap_targets(plan: FractalPlanCapsule, repo_root: str | Path) -> None:
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
    new = '''def _refresh_plan_codemap_targets(plan: FractalPlanCapsule, repo_root: str | Path) -> None:
    root = Path(repo_root)
    # Refresh may maintain an existing navigation artifact, but it must not
    # manufacture the artifact whose presence is itself the grounding boundary.
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
    ARCHITECT.write_text(replace_once(text, old, new, "Architect fail-closed refresh"), encoding="utf-8")


def patch_navigator_commands() -> None:
    text = NAV.read_text(encoding="utf-8")
    old_mentions = '''def _command_mentions(text: str) -> list[str]:
    commands: list[str] = []
    for match in re.finditer(r"(?m)^\\s*(python(?:3)?\\s+-m\\s+[A-Za-z0-9_\\.]+|python(?:3)?\\s+[A-Za-z0-9_./-]+\\.py[^\\n]*)", text):
        command = " ".join(match.group(1).strip().split())
        if command and command not in commands:
            commands.append(command)
    return commands[:20]
'''
    new_mentions = '''def _command_mentions(text: str) -> list[str]:
    commands: list[str] = []
    for match in re.finditer(r"(?m)^\\s*(python(?:3)?\\s+-m\\s+[A-Za-z0-9_\\.]+|python(?:3)?\\s+[A-Za-z0-9_./-]+\\.py[^\\n]*)", text):
        command = " ".join(match.group(1).strip().split())
        if command and command not in commands:
            commands.append(command)
    # REPL/bang commands are semantic command surfaces too. Keep the token
    # bounded and auditable; source locations are resolved separately.
    for match in re.finditer(r"(?<![A-Za-z0-9_])![A-Za-z][A-Za-z0-9_-]*", text):
        command = match.group(0)
        if command not in commands:
            commands.append(command)
    return commands[:20]
'''
    text = replace_once(text, old_mentions, new_mentions, "bang command extraction")

    old_locations = '''def _command_locations(text: str, commands: list[str]) -> dict[str, list[int]]:
    """Return stable 1-based line references for extracted commands."""
    lines = text.splitlines()
    locations: dict[str, list[int]] = {}
    for command in commands:
        needle = " ".join(command.strip().split())
        hits = [
            index
            for index, line in enumerate(lines, start=1)
            if " ".join(line.strip().split()).startswith(needle)
        ]
        if hits:
            locations[command] = hits[:8]
    return locations
'''
    new_locations = '''def _command_locations(text: str, commands: list[str]) -> dict[str, list[int]]:
    """Return stable 1-based line references for extracted commands."""
    lines = text.splitlines()
    locations: dict[str, list[int]] = {}
    for command in commands:
        needle = " ".join(command.strip().split())
        if needle.startswith("!"):
            pattern = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(needle)}(?![A-Za-z0-9_-])")
            hits = [index for index, line in enumerate(lines, start=1) if pattern.search(line)]
        else:
            hits = [
                index
                for index, line in enumerate(lines, start=1)
                if " ".join(line.strip().split()).startswith(needle)
            ]
        if hits:
            locations[command] = hits[:8]
    return locations
'''
    text = replace_once(text, old_locations, new_locations, "command source locations")

    old_index = '''def _command_index(cards: list[dict[str, Any]]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = defaultdict(list)
    for card in cards:
        for command in card.get("commands", []):
            if card["path"] not in out[command]:
                out[command].append(card["path"])
    return dict(out)
'''
    new_index = '''def _command_index(cards: list[dict[str, Any]]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = defaultdict(list)
    for card in cards:
        path = str(card["path"])
        line_map = card.get("command_lines", {}) or {}
        for command in card.get("commands", []):
            lines = line_map.get(command, []) or []
            locations = [f"{path}:{int(line)}" for line in lines[:8]] if lines else [path]
            for location in locations:
                if location not in out[command]:
                    out[command].append(location)
    return dict(out)
'''
    NAV.write_text(replace_once(text, old_index, new_index, "source-resolvable command index"), encoding="utf-8")


def patch_incremental_refresh() -> None:
    text = NAV.read_text(encoding="utf-8")

    old_cards = '''    cards = [dict(card) for card in payload.get("files", []) if isinstance(card, dict)]
    card_by_path = {str(card.get("path") or ""): card for card in cards if card.get("path")}
    changed_rel_paths: list[str] = []
'''
    new_cards = '''    cards = [dict(card) for card in payload.get("files", []) if isinstance(card, dict)]
    card_by_path = {str(card.get("path") or ""): card for card in cards if card.get("path")}

    # Committed file cards are intentionally compact and omit full symbol records.
    # Rehydrate untouched symbol records from the existing canonical symbol index
    # before replacing only the changed paths; otherwise an incremental refresh
    # silently erases unrelated symbols from the rebuilt index.
    symbol_index = payload.get("symbol_index", {})
    if isinstance(symbol_index, dict):
        for name, raw_entries in symbol_index.items():
            entries = raw_entries if isinstance(raw_entries, list) else [raw_entries]
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                file_path = str(entry.get("file") or "")
                card = card_by_path.get(file_path)
                if card is None:
                    continue
                symbols = card.setdefault("symbols", [])
                if not isinstance(symbols, list):
                    symbols = []
                    card["symbols"] = symbols
                semantic_id = str(entry.get("semantic_id") or "")
                if semantic_id and any(
                    isinstance(existing, dict) and str(existing.get("semantic_id") or "") == semantic_id
                    for existing in symbols
                ):
                    continue
                symbols.append({
                    "name": str(name),
                    "kind": entry.get("kind"),
                    "line": entry.get("line"),
                    "end_line": entry.get("end_line"),
                    "semantic_id": entry.get("semantic_id"),
                    "signature_hash": entry.get("signature_hash"),
                })

    changed_rel_paths: list[str] = []
'''
    text = replace_once(text, old_cards, new_cards, "incremental symbol rehydration")

    old_hash_refresh = '''    refresh = canonical.get("incremental_refresh")
    if isinstance(refresh, dict):
        refresh.pop("payload_hash", None)
'''
    new_hash_refresh = '''    # Incremental bookkeeping is evidence about how the current semantic state
    # was reached, not part of the semantic CODEMAP state itself. Excluding the
    # entire block lets a true no-op refresh remain byte- and mtime-stable.
    canonical.pop("incremental_refresh", None)
'''
    text = replace_once(text, old_hash_refresh, new_hash_refresh, "semantic payload hash")

    old_existing = '''    else:
        payload = _load_json(absolute_index)
        topology = None
        if include_topology:
            topology, _ = load_or_compile_topology(
                repo_root,
                topology_path=topology_path,
                refresh=refresh_topology,
            )
        payload = refresh_index_for_paths(payload, repo_root, changed_paths, topology=topology)
    write_navigation_artifacts(payload, absolute_index, absolute_markdown)
    return payload
'''
    new_existing = '''    else:
        original_payload = _load_json(absolute_index)
        topology = None
        if include_topology:
            topology, _ = load_or_compile_topology(
                repo_root,
                topology_path=topology_path,
                refresh=refresh_topology,
            )
        refreshed_payload = refresh_index_for_paths(original_payload, repo_root, changed_paths, topology=topology)
        if _codemap_payload_hash(refreshed_payload) == _codemap_payload_hash(original_payload):
            return original_payload
        payload = refreshed_payload
    write_navigation_artifacts(payload, absolute_index, absolute_markdown)
    return payload
'''
    text = replace_once(text, old_existing, new_existing, "no-op refresh write suppression")

    NAV.write_text(text, encoding="utf-8")


def retire_historical_umc() -> None:
    UMC.parent.mkdir(parents=True, exist_ok=True)
    UMC.write_text('''name: UMC deep review v2 target materialize (historical)\n\n# Historical PR #193 exact-head materializer.\n# PR #193 is merged and its exact reviewed generation is no longer an active\n# development head. Keeping an automatic pull_request_target trigger here caused\n# definition-level/zero-job failures after the historical binding became stale.\n# Preserve this file as auditable provenance, but require explicit manual review\n# before any historical replay.\non:\n  workflow_dispatch:\n\npermissions:\n  contents: read\n\njobs:\n  historical-boundary:\n    runs-on: ubuntu-latest\n    steps:\n      - name: Explain historical boundary\n        shell: bash\n        run: |\n          cat <<'EOF'\n          This workflow is retained as provenance for the merged PR #193 deep-v2\n          materializer. Its former exact-head pull_request_target binding is\n          intentionally retired. Current continuity contracts are validated by\n          the active repository test suites and current CI workflows.\n          EOF\n''', encoding="utf-8")


def main() -> int:
    patch_architect()
    patch_navigator_commands()
    patch_incremental_refresh()
    retire_historical_umc()
    print("WO-FLEET-PHASE3 Triad2 patch applied in working tree")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
