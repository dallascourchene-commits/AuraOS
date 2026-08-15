from __future__ import annotations

from pathlib import Path


NAV = Path(__file__).resolve().parents[1] / "aura_codebase_navigator.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def main() -> int:
    text = NAV.read_text(encoding="utf-8")

    text = replace_once(
        text,
        '''            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                signature = _symbol_signature(child)
                kind = "method" if scope else "function"
''',
        '''            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                signature = _symbol_signature(child)
                if isinstance(child, ast.AsyncFunctionDef):
                    kind = "async_method" if scope else "async_function"
                else:
                    kind = "method" if scope else "function"
''',
        "async symbol identity",
    )

    text = replace_once(
        text,
        '''    if absolute.exists() and not refresh:
        try:
            existing = json.loads(absolute.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = None
        if isinstance(existing, dict) and is_deep(existing):
            return existing, "compiled_deep_topology"
''',
        '''    if absolute.exists() and not refresh:
        try:
            existing = json.loads(absolute.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = None
        if isinstance(existing, dict) and is_deep(existing):
            return existing, "compiled_deep_topology"
        # Preserve legacy topology when it is still source-indexable. This is a
        # compatibility read path only; refresh=True still recompiles deep topology.
        if isinstance(existing, dict) and _topology_file_index(existing):
            return existing, "source_indexable_topology"
''',
        "legacy source-indexable topology",
    )

    text = replace_once(
        text,
        '''def refresh_index_for_paths(
    payload: dict[str, Any],
    root: Path,
    changed_paths: list[str | Path],
    *,
    topology: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Refresh changed/deleted file branches without rebuilding unrelated file cards."""
''',
        '''def refresh_index_for_paths(
    payload: dict[str, Any] | str | Path,
    root_or_changed_paths: Path | list[str | Path],
    changed_paths: list[str | Path] | None = None,
    *,
    root: Path | None = None,
    topology: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Refresh changed/deleted file branches with current and legacy call compatibility."""
    legacy_call = root is not None
    if legacy_call:
        if changed_paths is not None:
            raise TypeError("changed_paths supplied both positionally and by legacy root form")
        repo_root = Path(root)
        resolved_changed_paths = (
            list(root_or_changed_paths)
            if isinstance(root_or_changed_paths, list)
            else [root_or_changed_paths]
        )
    else:
        repo_root = Path(root_or_changed_paths)
        if changed_paths is None:
            raise TypeError("changed_paths is required")
        resolved_changed_paths = changed_paths

    root = repo_root
    changed_paths = resolved_changed_paths
    if isinstance(payload, (str, Path)):
        payload = _load_json(Path(payload))
    if topology is None and legacy_call:
        legacy_topology_path = root / DEFAULT_TOPOLOGY_PATH
        try:
            topology = _load_json(legacy_topology_path) if legacy_topology_path.exists() else None
        except (OSError, ValueError, json.JSONDecodeError):
            topology = None
    if topology is None:
        try:
            topology, _ = load_or_compile_topology(root, refresh=False)
        except (OSError, RuntimeError, ValueError, json.JSONDecodeError):
            topology = None
''',
        "incremental refresh dual-call contract",
    )

    text = replace_once(
        text,
        '''    refreshed["incremental_refresh"]["payload_hash"] = _codemap_payload_hash(refreshed)
    return refreshed
''',
        '''    refreshed["incremental_refresh"]["payload_hash"] = _codemap_payload_hash(refreshed)
    # Legacy callers consume last_refresh; keep it as a projection of the single
    # incremental-refresh truth rather than a second state plane.
    refreshed["last_refresh"] = {
        "mode": "incremental_ast_hook",
        "refreshed_paths": sorted(set(changed_rel_paths)),
    }
    return refreshed
''',
        "legacy last_refresh projection",
    )

    text = replace_once(
        text,
        '''def _attach_topology(cards: list[dict[str, Any]], topology_index: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    for card in cards:
        card["topology"] = topology_index.get(card["path"], {})
    return cards
''',
        '''def _attach_topology(
    cards: list[dict[str, Any]],
    topology_index: dict[str, Any],
) -> list[dict[str, Any]] | dict[str, dict[str, Any]]:
    raw_topology = "nodes" in topology_index or "edges" in topology_index
    normalized = _topology_file_index(topology_index) if raw_topology else topology_index
    for card in cards:
        card["topology"] = normalized.get(card["path"], {})
    # Current build callers pass a normalized index and receive cards. Historical
    # callers passed raw topology and consumed the normalized per-file index.
    return normalized if raw_topology else cards
''',
        "topology attachment compatibility",
    )

    text = replace_once(
        text,
        '''def search_index(index: dict[str, Any], query: str, *, top_n: int = 12) -> list[dict[str, Any]]:
    query_vector = stable_unit_vector(query)
''',
        '''def search_index(
    index: dict[str, Any],
    query: str,
    *,
    top_n: int = 12,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    if limit is not None:
        top_n = int(limit)
    exact_command = query.strip()
    command_index = index.get("command_index", {})
    if exact_command.startswith("!") and isinstance(command_index, dict) and exact_command in command_index:
        authoritative_paths: list[str] = []
        for raw in command_index.get(exact_command, []) or []:
            location = str(raw)
            path = re.sub(r":\\d+$", "", location)
            if path and path not in authoritative_paths:
                authoritative_paths.append(path)
        by_path = {
            str(card.get("path") or ""): card
            for card in index.get("files", [])
            if isinstance(card, dict)
        }
        matching_paths = list(authoritative_paths)
        for card in index.get("files", []):
            if not isinstance(card, dict):
                continue
            path = str(card.get("path") or "")
            if exact_command in (card.get("commands", []) or []) and path not in matching_paths:
                matching_paths.append(path)
        compact_hits: list[dict[str, Any]] = []
        for path in matching_paths[:top_n]:
            card = dict(by_path.get(path, {}))
            if not card:
                continue
            card.pop("commands", None)
            lines = (card.get("command_lines", {}) or {}).get(exact_command, [])
            card["matched_command_lines"] = {exact_command: list(lines)}
            compact_hits.append(card)
        if compact_hits:
            return compact_hits
    query_vector = stable_unit_vector(query)
''',
        "compact exact-command query compatibility",
    )

    NAV.write_text(text, encoding="utf-8")
    print("WC-02 Phase4 navigator compatibility adapters applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
