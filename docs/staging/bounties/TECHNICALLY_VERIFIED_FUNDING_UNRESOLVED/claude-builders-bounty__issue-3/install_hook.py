#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
SETTINGS = HOME / ".claude" / "settings.json"
COMMAND = "python3 ~/.claude/hooks/block_destructive.py"
ENTRY = {"matcher": "Bash", "hooks": [{"type": "command", "command": COMMAND}]}


def main() -> int:
    SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    if SETTINGS.exists():
        data = json.loads(SETTINGS.read_text(encoding="utf-8"))
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        shutil.copy2(SETTINGS, SETTINGS.with_name(f"settings.json.bak.{stamp}"))
    else:
        data = {}

    hooks = data.setdefault("hooks", {})
    pre = hooks.setdefault("PreToolUse", [])
    if not any(
        isinstance(item, dict)
        and item.get("matcher") == "Bash"
        and any(
            isinstance(hook, dict) and hook.get("command") == COMMAND
            for hook in item.get("hooks", [])
        )
        for item in pre
    ):
        pre.append(ENTRY)

    SETTINGS.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Installed PreToolUse hook in {SETTINGS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
