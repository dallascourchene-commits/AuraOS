from __future__ import annotations

from pathlib import Path
import re


def main() -> None:
    path = Path("aura_agent_arena_mcp.py")
    text = path.read_text(encoding="utf-8")
    marker = '''    return decorator


# ---------------------------------------------------------------------------
# Tool definitions (for tools/list)
'''
    helper = '''    return decorator


def _strict_bool_arg(
    args: dict[str, Any],
    key: str,
    *,
    default: bool,
) -> bool:
    value = args.get(key)
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise ValueError(f"{key} must be a boolean")


# ---------------------------------------------------------------------------
# Tool definitions (for tools/list)
'''
    if marker not in text:
        raise SystemExit("MCP strict-boolean helper marker not found")
    text = text.replace(marker, helper, 1)
    text = re.sub(
        r'bool\(args\.get\("([^"]+)",\s*(True|False)\)\)',
        r'_strict_bool_arg(args, "\1", default=\2)',
        text,
    )
    multiline = {
        '''bool(
            args.get("emergent_include_research_plan", True)
        )''': '''_strict_bool_arg(
            args, "emergent_include_research_plan", default=True
        )''',
        '''bool(
            args.get("include_offline_research", True)
        )''': '''_strict_bool_arg(
            args, "include_offline_research", default=True
        )''',
    }
    for old, new in multiline.items():
        text = text.replace(old, new)
    if "bool(args.get(" in text:
        raise SystemExit("unhardened MCP boolean argument remains")
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
