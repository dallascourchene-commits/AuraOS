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
    """Extract executable CLI lines and Aura bang-command tokens deterministically."""
    commands: list[str] = []
    for match in re.finditer(r"(?m)^\\s*(python(?:3)?\\s+-m\\s+[A-Za-z0-9_\\.]+|python(?:3)?\\s+[A-Za-z0-9_./-]+\\.py[^\\n]*)", text):
        command = " ".join(match.group(1).strip().split())
        if command and command not in commands:
            commands.append(command)
    for match in re.finditer(r"(?<!\\w)![A-Za-z_][\\w-]*", text):
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
    """Return stable 1-based source lines for extracted commands."""
    lines = text.splitlines()
    locations: dict[str, list[int]] = {}
    for command in commands:
        needle = " ".join(command.strip().split())
        if command.startswith("!"):
            hits = [
                index
                for index, line in enumerate(lines, start=1)
                if command in line
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
    return dict(out)
'''

NEW_INDEX = '''def _command_index(cards: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Map commands to exact file:line source locators when available."""
    out: dict[str, list[str]] = defaultdict(list)
    for card in cards:
        path = str(card.get("path") or "")
        command_lines = card.get("command_lines", {}) or {}
        for command in card.get("commands", []):
            lines = command_lines.get(command, []) if isinstance(command_lines, dict) else []
            locators = [f"{path}:{int(line)}" for line in lines] if lines else [path]
            for locator in locators:
                if locator and locator not in out[command]:
                    out[command].append(locator)
    return {command: locations for command, locations in sorted(out.items())}
'''


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one anchor, found {count}")
    return text.replace(old, new, 1)


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    text = replace_once(text, OLD_MENTIONS, NEW_MENTIONS, "command mentions")
    text = replace_once(text, OLD_LOCATIONS, NEW_LOCATIONS, "command locations")
    text = replace_once(text, OLD_INDEX, NEW_INDEX, "command index")
    TARGET.write_text(text, encoding="utf-8")
    Path(__file__).unlink()
    print("CODEMAP bang-command source index restored")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
