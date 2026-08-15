from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "aura_skillweaver.py"

ANCHOR = '''            for sym in cmap.get("symbols", []):
                skills.append(AuraSkill(
                    name=sym.get("name", ""),
                    kind="function",
                    path=sym.get("file", ""),
                    symbol=sym.get("name", ""),
                    description=sym.get("signature", ""),
                    categories=["symbol"],
                ))
        except (json.JSONDecodeError, KeyError):
            pass
'''

REPLACEMENT = '''            for sym in cmap.get("symbols", []):
                skills.append(AuraSkill(
                    name=sym.get("name", ""),
                    kind="function",
                    path=sym.get("file", ""),
                    symbol=sym.get("name", ""),
                    description=sym.get("signature", ""),
                    categories=["symbol"],
                ))

            # CODEMAP.json is the canonical machine navigation index. Command
            # locations may be line-qualified (path:line) for Fusion symbol
            # resolution; SkillWeaver intentionally normalizes them back to the
            # underlying source path because its registry models capabilities,
            # not exact source spans.
            seen_commands = {skill.name for skill in skills if skill.kind == "command"}
            command_index = cmap.get("command_index", {})
            if isinstance(command_index, dict):
                for command, raw_locations in command_index.items():
                    if not isinstance(command, str) or not command.startswith("!"):
                        continue
                    locations = raw_locations if isinstance(raw_locations, list) else [raw_locations]
                    first = next((str(value) for value in locations if value), "")
                    file_part = re.sub(r":\\d+$", "", first)
                    if command in seen_commands:
                        continue
                    skills.append(AuraSkill(
                        name=command,
                        kind="command",
                        path=file_part or None,
                        symbol=command,
                        description="Bang command " + command,
                        categories=["command"],
                    ))
                    seen_commands.add(command)
        except (json.JSONDecodeError, KeyError):
            pass
'''


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    count = text.count(ANCHOR)
    if count != 1:
        raise RuntimeError(f"SkillWeaver CODEMAP command anchor expected once, found {count}")
    TARGET.write_text(text.replace(ANCHOR, REPLACEMENT, 1), encoding="utf-8")
    print("Phase-3 SkillWeaver canonical CODEMAP command registry repair applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
