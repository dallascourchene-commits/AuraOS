from __future__ import annotations

from pathlib import Path


def replace_required(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"missing Waboose repair target: {label}")
    return text.replace(old, new, 1)


def repair_bridge() -> None:
    path = Path("aura_agent_arena_persistence_bridge.py")
    text = path.read_text(encoding="utf-8")
    text = replace_required(
        text,
        "from typing import Any, Mapping\n",
        "from collections.abc import Mapping\nfrom typing import Any\n",
        "persistence Mapping import",
    )
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def repair_mcp() -> None:
    path = Path("aura_agent_arena_mcp.py")
    text = path.read_text(encoding="utf-8")
    text = replace_required(
        text,
        "import json\nimport logging\nimport sys\nfrom typing import Any, Mapping\n",
        "from collections.abc import Mapping\nimport json\nimport logging\nimport sys\nfrom typing import Any\n",
        "MCP Mapping import and ordering",
    )
    text = replace_required(
        text,
        "        except Exception as exc:  # noqa: BLE001\n",
        "        except Exception as exc:\n",
        "unused MCP BLE001 directive",
    )
    text = replace_required(
        text,
        "    for line in sys.stdin:\n        line = line.strip()\n        if not line:\n",
        "    for raw_line in sys.stdin:\n        line = raw_line.strip()\n        if not line:\n",
        "MCP loop variable overwrite",
    )
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def main() -> None:
    repair_bridge()
    repair_mcp()


if __name__ == "__main__":
    main()
