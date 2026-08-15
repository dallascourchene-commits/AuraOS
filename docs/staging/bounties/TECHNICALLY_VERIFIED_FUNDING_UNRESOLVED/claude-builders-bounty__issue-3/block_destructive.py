#!/usr/bin/env python3
"""Claude Code PreToolUse hook that blocks a small, explicit destructive-command set."""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("rm -rf", re.compile(r"(?i)(?:^|[;&|]\s*)rm\s+(?:(?:-[^\s;&|]*[rR][^\s;&|]*[fF][^\s;&|]*)|(?:-[^\s;&|]*[fF][^\s;&|]*[rR][^\s;&|]*)|(?:-r\s+-f)|(?:-f\s+-r))(?:\s|$)")),
    ("DROP TABLE", re.compile(r"(?i)\bDROP\s+TABLE\b")),
    ("git push --force", re.compile(r"(?i)\bgit\s+push\b[^\n;&|]*?(?:--force(?:-with-lease)?|-f)(?:\s|$)")),
    ("TRUNCATE", re.compile(r"(?i)\bTRUNCATE(?:\s+TABLE)?\b")),
)
DELETE_FROM = re.compile(r"(?i)\bDELETE\s+FROM\b")
WHERE = re.compile(r"(?i)\bWHERE\b")
SEGMENT_END = re.compile(r"(?:;|&&|\|\||\n)")


def _delete_without_where(command: str) -> bool:
    for match in DELETE_FROM.finditer(command):
        tail = command[match.end():]
        end = SEGMENT_END.search(tail)
        segment = tail[: end.start()] if end else tail
        if not WHERE.search(segment):
            return True
    return False


def classify(command: str) -> str | None:
    for label, pattern in RULES:
        if pattern.search(command):
            return label
    if _delete_without_where(command):
        return "DELETE FROM without WHERE"
    return None


def _log_block(command: str, cwd: str, rule: str) -> None:
    log_path = Path.home() / ".claude" / "hooks" / "blocked.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()
    safe_command = command.replace("\n", "\\n")
    safe_cwd = cwd.replace("\n", "\\n")
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"{timestamp}\trule={rule}\tproject={safe_cwd}\tcommand={safe_command}\n")


def _deny(reason: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }, separators=(",", ":")))


def main() -> int:
    try:
        payload: dict[str, Any] = json.load(sys.stdin)
    except Exception as exc:
        _deny(f"Safety hook could not parse tool input; command blocked ({type(exc).__name__}).")
        return 0

    if payload.get("tool_name") != "Bash":
        return 0

    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        _deny("Safety hook received malformed Bash tool input; command blocked.")
        return 0

    command = tool_input.get("command")
    if not isinstance(command, str):
        _deny("Safety hook received Bash input without a string command; command blocked.")
        return 0

    rule = classify(command)
    if rule is None:
        return 0

    cwd_value = payload.get("cwd")
    cwd = cwd_value if isinstance(cwd_value, str) else os.getcwd()
    _log_block(command, cwd, rule)
    _deny(f"Destructive command blocked by safety hook: {rule}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
