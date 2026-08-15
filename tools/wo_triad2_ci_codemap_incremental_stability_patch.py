from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "aura_codebase_navigator.py"

OLD_COMPACT = '''def _compact_file_cards(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    for card in cards:
        compact.append({
            "path": card["path"],
            "role": card["role"],
            "bytes": card["bytes"],
            "lines": card["lines"],
            "tokens_est": card["tokens_est"],
            "binary": bool(card.get("binary", False)),
            "symbol_count": len(card.get("symbols", [])),
            "commands": card.get("commands", []),
            "command_lines": card.get("command_lines", {}),
            "topology": card.get("topology", {}),
            "digest8": card.get("digest8"),
            "vector": card.get("vector", []),
        })
    return compact
'''

NEW_COMPACT = '''def _compact_file_cards(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Persist enough source metadata for lossless incremental CODEMAP refreshes."""
    compact: list[dict[str, Any]] = []
    for card in cards:
        symbols = [dict(symbol) for symbol in card.get("symbols", []) if isinstance(symbol, dict)]
        compact.append({
            "path": card["path"],
            "role": card["role"],
            "bytes": card["bytes"],
            "lines": card["lines"],
            "tokens_est": card["tokens_est"],
            "binary": bool(card.get("binary", False)),
            "symbol_count": len(symbols),
            "symbols": symbols,
            "commands": card.get("commands", []),
            "command_lines": card.get("command_lines", {}),
            "topology": card.get("topology", {}),
            "digest8": card.get("digest8"),
            "vector": card.get("vector", []),
        })
    return compact
'''

OLD_HASH = '''def _codemap_payload_hash(payload: dict[str, Any]) -> str:
    canonical = json.loads(json.dumps(payload))
    canonical.pop("generated_at_unix", None)
    summary = canonical.get("summary")
    if isinstance(summary, dict):
        summary.pop("elapsed_ms", None)
    refresh = canonical.get("incremental_refresh")
    if isinstance(refresh, dict):
        refresh.pop("payload_hash", None)
    raw = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.blake2b(raw, digest_size=16).hexdigest()
'''

NEW_HASH = '''def _codemap_payload_hash(payload: dict[str, Any]) -> str:
    """Hash logical navigation content, excluding generation/refresh bookkeeping."""
    canonical = json.loads(json.dumps(payload))
    canonical.pop("generated_at_unix", None)
    canonical.pop("incremental_refresh", None)
    summary = canonical.get("summary")
    if isinstance(summary, dict):
        summary.pop("elapsed_ms", None)
    raw = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.blake2b(raw, digest_size=16).hexdigest()
'''

OLD_REFRESH = '''    if not absolute_index.exists():
        payload = build_navigation_system(
            repo_root,
            include_topology=include_topology,
            topology_path=topology_path,
            refresh_topology=refresh_topology,
        )
    else:
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

NEW_REFRESH = '''    if not absolute_index.exists():
        payload = build_navigation_system(
            repo_root,
            include_topology=include_topology,
            topology_path=topology_path,
            refresh_topology=refresh_topology,
        )
        write_navigation_artifacts(payload, absolute_index, absolute_markdown)
        return payload

    existing_payload = _load_json(absolute_index)
    topology = None
    if include_topology:
        topology, _ = load_or_compile_topology(
            repo_root,
            topology_path=topology_path,
            refresh=refresh_topology,
        )
    refreshed = refresh_index_for_paths(existing_payload, repo_root, changed_paths, topology=topology)
    if _codemap_payload_hash(refreshed) == _codemap_payload_hash(existing_payload):
        return existing_payload
    write_navigation_artifacts(refreshed, absolute_index, absolute_markdown)
    return refreshed
'''


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one anchor, found {count}")
    return text.replace(old, new, 1)


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    text = replace_once(text, OLD_COMPACT, NEW_COMPACT, "compact file cards")
    text = replace_once(text, OLD_HASH, NEW_HASH, "payload hash")
    text = replace_once(text, OLD_REFRESH, NEW_REFRESH, "refresh write gate")
    TARGET.write_text(text, encoding="utf-8")
    Path(__file__).unlink()
    print("CODEMAP incremental refresh preserves symbols and skips unchanged artifact writes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
