from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "aura_codebase_navigator.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one anchor, found {count}")
    return text.replace(old, new, 1)


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")

    text = replace_once(
        text,
        '            "symbol_count": len(card.get("symbols", [])),',
        '            "symbol_count": len(card.get("symbols", [])) if "symbols" in card else int(card.get("symbol_count", 0)),',
        "compact symbol count preservation",
    )

    text = replace_once(
        text,
        '''    refreshed["symbol_index"] = _symbol_index(refreshed_cards)
    refreshed["command_index"] = _command_index(refreshed_cards)
''',
        '''    changed_set = set(changed_rel_paths)
    merged_symbol_index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    existing_symbol_index = payload.get("symbol_index", {})
    if isinstance(existing_symbol_index, dict):
        for name, entries in existing_symbol_index.items():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                if str(entry.get("file") or "") in changed_set:
                    continue
                merged_symbol_index[str(name)].append(dict(entry))
    for card in refreshed_cards:
        if str(card.get("path") or "") not in changed_set:
            continue
        for symbol in card.get("symbols", []):
            if not isinstance(symbol, dict):
                continue
            merged_symbol_index[str(symbol.get("name", ""))].append({
                "file": card.get("path"),
                "kind": symbol.get("kind"),
                "line": symbol.get("line"),
                "end_line": symbol.get("end_line"),
                "semantic_id": symbol.get("semantic_id"),
                "signature_hash": symbol.get("signature_hash"),
            })
    refreshed["symbol_index"] = {
        name: sorted(entries, key=lambda item: (str(item.get("file") or ""), int(item.get("line") or 0), str(item.get("semantic_id") or "")))
        for name, entries in sorted(merged_symbol_index.items())
        if name
    }
    refreshed["command_index"] = _command_index(refreshed_cards)
''',
        "incremental symbol index preservation",
    )

    text = replace_once(
        text,
        '    records = _records_from_cards(refreshed_cards)\n',
        '    records = _records_from_cards([card for card in refreshed_cards if str(card.get("path") or "") in changed_set])\n',
        "incremental changed-record scope",
    )

    text = replace_once(
        text,
        '''    refresh = canonical.get("incremental_refresh")
    if isinstance(refresh, dict):
        refresh.pop("payload_hash", None)
''',
        '''    # Refresh provenance is operational bookkeeping, not canonical CODEMAP state.
    canonical.pop("incremental_refresh", None)
''',
        "canonical refresh hash",
    )

    text = replace_once(
        text,
        '''    else:
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
''',
        '''    else:
        previous_payload = _load_json(absolute_index)
        topology = None
        if include_topology:
            topology, _ = load_or_compile_topology(
                repo_root,
                topology_path=topology_path,
                refresh=refresh_topology,
            )
        payload = refresh_index_for_paths(previous_payload, repo_root, changed_paths, topology=topology)
        if _codemap_payload_hash(payload) == _codemap_payload_hash(previous_payload):
            return previous_payload
    write_navigation_artifacts(payload, absolute_index, absolute_markdown)
    return payload
''',
        "no-op refresh artifact preservation",
    )

    TARGET.write_text(text, encoding="utf-8")
    Path(__file__).unlink()
    print("CODEMAP incremental refresh preserves canonical no-op state")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
