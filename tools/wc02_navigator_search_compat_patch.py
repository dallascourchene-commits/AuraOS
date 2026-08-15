from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "aura_codebase_navigator.py"
SEARCH_START = "def search_index("
SEARCH_END = "\n\ndef write_navigation_artifacts"

ATTACH_OLD = '''def _attach_topology(cards: list[dict[str, Any]], topology_index: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    for card in cards:
        card["topology"] = topology_index.get(card["path"], {})
    return cards
'''

ATTACH_NEW = '''def _attach_topology(
    cards: list[dict[str, Any]],
    topology_or_index: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Attach normalized per-file topology and return the file index.

    Historical callers pass the raw topology graph; current internal callers may
    already have a normalized file index. Supporting both keeps the helper
    backward compatible without re-scanning source files.
    """
    if "nodes" in topology_or_index or "edges" in topology_or_index:
        topology_index = _topology_file_index(topology_or_index)
    else:
        topology_index = topology_or_index
    for card in cards:
        card["topology"] = topology_index.get(str(card.get("path", "")), {})
    return topology_index
'''

BUILD_OLD = '''        topology_index = _topology_file_index(topology)
        cards = _attach_topology(cards, topology_index)
'''
BUILD_NEW = '''        topology_index = _topology_file_index(topology)
        _attach_topology(cards, topology_index)
'''

SEARCH_REPLACEMENT = '''def search_index(
    index: dict[str, Any],
    query: str,
    *,
    top_n: int = 12,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Rank compact file cards without rescanning source files.

    ``limit`` is the historical keyword retained for compatibility; ``top_n``
    is the current CLI-facing spelling. Exact command queries use the canonical
    command index and return compact source-location hits before semantic rank.
    """
    result_limit = top_n if limit is None else limit
    if not isinstance(result_limit, int) or isinstance(result_limit, bool) or result_limit < 1:
        raise ValueError("search result limit must be a positive integer")
    terms = {term.lower() for term in re.findall(r"[A-Za-z0-9_!:-]+", query)}
    qvec = stable_unit_vector(query)
    symbol_hits = index.get("symbol_index", {})
    command_hits = index.get("command_index", {})
    target_files: Counter[str] = Counter()
    for term in terms:
        if term in command_hits:
            target_files.update({str(path).split(":", 1)[0]: 12 for path in command_hits[term]})
        for symbol, hits in symbol_hits.items():
            if term == symbol.lower():
                target_files.update({hit["file"]: 10 for hit in hits})
    ranked: list[dict[str, Any]] = []
    for card in index.get("files", []):
        topology = card.get("topology", {}) or {}
        haystack = " ".join([
            str(card.get("path", "")),
            str(card.get("role", "")),
            " ".join(str(command) for command in card.get("commands", [])),
            " ".join(str(path) for path in topology.get("neighbor_files", [])),
            " ".join(str(kind) for kind in topology.get("edge_kinds", {}).keys()),
        ]).lower()
        lexical = sum(1 for term in terms if term in haystack)
        path = str(card.get("path", ""))
        path_exact = sum(3 for term in terms if term and term in path.lower())
        topology_boost = min(3, float(topology.get("degree", 0)) / 100) if lexical else 0
        role_boost = 2 if card.get("role") == "python_module" and target_files[path] else 0
        test_penalty = 4 if path.startswith("test_") and target_files[path] else 0
        score = (
            target_files[path] + role_boost + lexical + path_exact + topology_boost
            + cosine(qvec, list(card.get("vector", []))) - test_penalty
        )
        if score > 0:
            result = {
                "score": round(score, 4),
                **{k: v for k, v in card.items() if k not in {"vector", "command_lines"}},
            }
            matched_commands = {term for term in terms if term in card.get("command_lines", {})}
            if matched_commands:
                result.pop("commands", None)
                result["matched_command_lines"] = {
                    command: card["command_lines"][command] for command in sorted(matched_commands)
                }
            ranked.append(result)
    return sorted(ranked, key=lambda item: (-item["score"], str(item.get("path", ""))))[:result_limit]
'''


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    text = replace_once(text, ATTACH_OLD, ATTACH_NEW, "_attach_topology")
    text = replace_once(text, BUILD_OLD, BUILD_NEW, "build_navigation_system attachment")

    start = text.find(SEARCH_START)
    if start < 0:
        raise RuntimeError("search_index start marker missing")
    end = text.find(SEARCH_END, start)
    if end < 0:
        raise RuntimeError("search_index end marker missing")
    current = text[start:end]
    if current != SEARCH_REPLACEMENT.rstrip("\n"):
        text = text[:start] + SEARCH_REPLACEMENT.rstrip("\n") + text[end:]

    TARGET.write_text(text, encoding="utf-8")
    print("WC-02 navigator API compatibility applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
