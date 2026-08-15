from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAV = ROOT / "aura_codebase_navigator.py"


def replace_region(text: str, start_marker: str, end_marker: str, replacement: str, label: str) -> str:
    start = text.find(start_marker)
    if start < 0:
        raise RuntimeError(f"{label}: start marker missing")
    end = text.find(end_marker, start)
    if end < 0:
        raise RuntimeError(f"{label}: end marker missing")
    return text[:start] + replacement.rstrip() + "\n\n" + text[end:]


def main() -> int:
    text = NAV.read_text(encoding="utf-8")

    mentions = '''def _command_mentions(text: str) -> list[str]:
    commands: list[str] = []
    for match in re.finditer(r"(?m)^\\s*(python(?:3)?\\s+-m\\s+[A-Za-z0-9_\\.]+|python(?:3)?\\s+[A-Za-z0-9_./-]+\\.py[^\\n]*)", text):
        command = " ".join(match.group(1).strip().split())
        if command and command not in commands:
            commands.append(command)
    # REPL/operator bang commands are navigation anchors too. They may occur
    # inside implementation strings, docs, or examples rather than at line start.
    for match in re.finditer(r"(?<![A-Za-z0-9_])![A-Za-z][A-Za-z0-9_-]*", text):
        command = match.group(0)
        if command not in commands:
            commands.append(command)
    return commands[:20]
'''
    text = replace_region(text, "def _command_mentions(text: str)", "def _command_locations(", mentions, "bang command mentions")

    locations = '''def _command_locations(text: str, commands: list[str]) -> dict[str, list[int]]:
    """Return stable 1-based line references for extracted commands."""
    lines = text.splitlines()
    locations: dict[str, list[int]] = {}
    for command in commands:
        needle = " ".join(command.strip().split())
        if needle.startswith("!"):
            hits = [
                index
                for index, line in enumerate(lines, start=1)
                if needle.lower() in line.lower()
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
    text = replace_region(text, "def _command_locations(text: str, commands: list[str])", "def load_or_compile_topology(", locations, "bang command locations")

    NAV.write_text(text, encoding="utf-8")
    print("CODEMAP bang-command index compatibility restored")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
