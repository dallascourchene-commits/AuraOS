from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "aura_codebase_navigator.py"

MENTIONS_ANCHOR = '''def _command_mentions(text: str) -> list[str]:
    commands: list[str] = []
    for match in re.finditer(r"(?m)^\\s*(python(?:3)?\\s+-m\\s+[A-Za-z0-9_\\.]+|python(?:3)?\\s+[A-Za-z0-9_./-]+\\.py[^\\n]*)", text):
        command = " ".join(match.group(1).strip().split())
        if command and command not in commands:
            commands.append(command)
    return commands[:20]
'''

MENTIONS_REPLACEMENT = '''def _command_mentions(text: str) -> list[str]:
    """Extract executable shell commands and Aura bang commands in source order."""
    located: list[tuple[int, str]] = []
    for match in re.finditer(r"(?m)^\\s*(python(?:3)?\\s+-m\\s+[A-Za-z0-9_\\.]+|python(?:3)?\\s+[A-Za-z0-9_./-]+\\.py[^\\n]*)", text):
        command = " ".join(match.group(1).strip().split())
        if command:
            located.append((match.start(1), command))
    for match in re.finditer(r"(?<!\\w)![A-Za-z_][\\w-]*", text):
        located.append((match.start(), match.group(0)))

    commands: list[str] = []
    for _offset, command in sorted(located, key=lambda item: (item[0], item[1])):
        if command not in commands:
            commands.append(command)
    return commands[:20]
'''

INDEX_ANCHOR = '''def _command_index(cards: list[dict[str, Any]]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = defaultdict(list)
    for card in cards:
        for command in card.get("commands", []):
            if card["path"] not in out[command]:
                out[command].append(card["path"])
    return dict(out)
'''

INDEX_REPLACEMENT = '''def _command_index(cards: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Map commands to source-resolvable path:line locations when available."""
    out: dict[str, list[str]] = defaultdict(list)
    for card in cards:
        path = str(card["path"])
        command_lines = card.get("command_lines", {})
        if not isinstance(command_lines, dict):
            command_lines = {}
        for command in card.get("commands", []):
            lines = command_lines.get(command, [])
            if isinstance(lines, int):
                lines = [lines]
            locations = [f"{path}:{int(line)}" for line in lines if isinstance(line, int) and line > 0]
            if not locations:
                locations = [path]
            for location in locations:
                if location not in out[command]:
                    out[command].append(location)
    return dict(out)
'''


def _replace_once(text: str, anchor: str, replacement: str, label: str) -> str:
    count = text.count(anchor)
    if count != 1:
        raise RuntimeError(f"Phase-3 {label} anchor expected once, found {count}")
    return text.replace(anchor, replacement, 1)


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    text = _replace_once(text, MENTIONS_ANCHOR, MENTIONS_REPLACEMENT, "command mention")
    text = _replace_once(text, INDEX_ANCHOR, INDEX_REPLACEMENT, "command index")
    TARGET.write_text(text, encoding="utf-8")
    print("Phase-3 CODEMAP bang-command + source-location repair applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
