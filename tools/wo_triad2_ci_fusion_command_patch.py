from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "aura_codebase_navigator.py"

OLD_MENTIONS = '''def _command_mentions(text: str) -> list[str]:
    commands: list[str] = []
    for match in re.finditer(r"(?m)^\\s*(python(?:3)?\\s+-m\\s+[A-Za-z0-9_\\.]+|python(?:3)?\\s+[A-Za-z0-9_./-]+\\.py[^\\n]*)", text):
        command = " ".join(match.group(1).strip().split())
        if command and command not in commands:
            commands.append(command)
    return commands[:20]
'''

NEW_MENTIONS = '''def _command_mentions(text: str) -> list[str]:
    """Extract source-groundable shell and Aura bang-command mentions."""
    commands: list[str] = []
    for match in re.finditer(r"(?m)^\\s*(python(?:3)?\\s+-m\\s+[A-Za-z0-9_\\.]+|python(?:3)?\\s+[A-Za-z0-9_./-]+\\.py[^\\n]*)", text):
        command = " ".join(match.group(1).strip().split())
        if command and command not in commands:
            commands.append(command)
    for match in re.finditer(r"(?<![A-Za-z0-9_-])![A-Za-z][A-Za-z0-9_-]*", text):
        command = match.group(0)
        if command not in commands:
            commands.append(command)
    return commands[:20]
'''

OLD_LOCATIONS = '''def _command_locations(text: str, commands: list[str]) -> dict[str, list[int]]:
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

NEW_LOCATIONS = '''def _command_locations(text: str, commands: list[str]) -> dict[str, list[int]]:
    """Return stable 1-based source references for extracted commands."""
    lines = text.splitlines()
    locations: dict[str, list[int]] = {}
    for command in commands:
        needle = " ".join(command.strip().split())
        if command.startswith("!"):
            pattern = re.compile(rf"(?<![A-Za-z0-9_-]){re.escape(command)}(?![A-Za-z0-9_-])")
            hits = [
                index
                for index, line in enumerate(lines, start=1)
                if pattern.search(line)
            ]
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

OLD_INDEX = '''def _command_index(cards: list[dict[str, Any]]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = defaultdict(list)
    for card in cards:
        for command in card.get("commands", []):
            if card["path"] not in out[command]:
                out[command].append(card["path"])
'''

NEW_INDEX = '''def _command_index(cards: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Map commands to source-resolvable path:line locations when available."""
    out: dict[str, list[str]] = defaultdict(list)
    for card in cards:
        path = str(card.get("path", ""))
        command_lines = card.get("command_lines", {})
        if not isinstance(command_lines, dict):
            command_lines = {}
        for command in card.get("commands", []):
            raw_lines = command_lines.get(command, [])
            if isinstance(raw_lines, int):
                raw_lines = [raw_lines]
            locations = [
                f"{path}:{int(line)}"
                for line in raw_lines
                if isinstance(line, int) or (isinstance(line, str) and line.isdigit())
            ]
            if not locations and path:
                locations = [path]
            for location in locations:
                if location not in out[command]:
                    out[command].append(location)
'''


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label} anchor expected once, found {count}")
    return text.replace(old, new, 1)


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    text = replace_once(text, OLD_MENTIONS, NEW_MENTIONS, "command mentions")
    text = replace_once(text, OLD_LOCATIONS, NEW_LOCATIONS, "command locations")
    text = replace_once(text, OLD_INDEX, NEW_INDEX, "command index")
    TARGET.write_text(text, encoding="utf-8")
    Path(__file__).unlink()
    print("Fusion bang-command CODEMAP source locations repaired")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
