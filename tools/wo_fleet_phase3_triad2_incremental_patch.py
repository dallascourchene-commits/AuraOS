from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAV = ROOT / "aura_codebase_navigator.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def main() -> int:
    text = NAV.read_text(encoding="utf-8")

    old_cards = '''    cards = [dict(card) for card in payload.get("files", []) if isinstance(card, dict)]
    card_by_path = {str(card.get("path") or ""): card for card in cards if card.get("path")}
    changed_rel_paths: list[str] = []
'''
    new_cards = '''    cards = [dict(card) for card in payload.get("files", []) if isinstance(card, dict)]
    card_by_path = {str(card.get("path") or ""): card for card in cards if card.get("path")}

    # Committed file cards are compact and may omit full symbol records. Rehydrate
    # untouched symbols from the current canonical index before replacing changed
    # paths, otherwise an incremental refresh can silently erase unrelated symbols.
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

    old_hash = '''    refresh = canonical.get("incremental_refresh")
    if isinstance(refresh, dict):
        refresh.pop("payload_hash", None)
'''
    new_hash = '''    # Refresh bookkeeping describes how the semantic state was reached; it is
    # not itself semantic CODEMAP state. Excluding it makes true no-op refreshes
    # byte- and mtime-stable.
    canonical.pop("incremental_refresh", None)
'''
    text = replace_once(text, old_hash, new_hash, "semantic payload hash")

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
    print("Phase-3 CODEMAP incremental no-op repair applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
