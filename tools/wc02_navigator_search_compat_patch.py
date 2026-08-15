from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "aura_codebase_navigator.py"
START = "def search_index("
END = "\n\ndef write_navigation_artifacts"

REPLACEMENT = '''def search_index(
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


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    start = text.find(START)
    if start < 0:
        raise RuntimeError("search_index start marker missing")
    end = text.find(END, start)
    if end < 0:
        raise RuntimeError("search_index end marker missing")
    current = text[start:end]
    if current == REPLACEMENT.rstrip("\n"):
        print("WC-02 navigator search compatibility already applied")
        return 0
    TARGET.write_text(text[:start] + REPLACEMENT.rstrip("\n") + text[end:], encoding="utf-8")
    print("WC-02 navigator search compatibility applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
