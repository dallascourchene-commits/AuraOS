from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "aura_skillweaver.py"

START = "    # 1. Parse CODEMAP.json for module/function entries\n"
END = "    # 3. Scan OUTPUT_FORMATS.md for output modes\n"

REPLACEMENT = '''    # 1. Parse canonical CODEMAP.json for modules, symbols, and commands.
    # Legacy surfaces remain read-only fallbacks; JSON is the current truth plane.
    codemap_json = os.path.join(repo_root, ".aura", "CODEMAP.json")
    json_commands_found = False
    if os.path.exists(codemap_json):
        try:
            with open(codemap_json, encoding="utf-8") as f:
                cmap = json.load(f)

            for entry in cmap.get("files", []):
                if not isinstance(entry, dict):
                    continue
                path = entry.get("path", "")
                role = entry.get("role", "")
                if role == "python_module" and path.endswith(".py"):
                    name = os.path.splitext(os.path.basename(path))[0]
                    deps_raw = entry.get("dependencies", [])
                    if isinstance(deps_raw, str):
                        deps = deps_raw.split(", ") if deps_raw else []
                    elif isinstance(deps_raw, list):
                        deps = [str(item) for item in deps_raw]
                    else:
                        deps = []
                    skills.append(AuraSkill(
                        name=name,
                        kind="module",
                        path=path,
                        symbol=None,
                        description=str(entry.get("synopsis", ""))[:200],
                        categories=[role],
                        dependencies=deps,
                    ))

            symbol_index = cmap.get("symbol_index")
            if isinstance(symbol_index, dict):
                for name, hits in symbol_index.items():
                    if not isinstance(hits, list):
                        continue
                    for hit in hits:
                        if not isinstance(hit, dict):
                            continue
                        skills.append(AuraSkill(
                            name=str(name),
                            kind="function",
                            path=str(hit.get("file", "")),
                            symbol=str(name),
                            description=str(hit.get("signature", "")),
                            categories=["symbol"],
                        ))
            else:
                # Legacy top-level symbol list, read compatibility only.
                for sym in cmap.get("symbols", []):
                    if not isinstance(sym, dict):
                        continue
                    skills.append(AuraSkill(
                        name=str(sym.get("name", "")),
                        kind="function",
                        path=str(sym.get("file", "")),
                        symbol=str(sym.get("name", "")),
                        description=str(sym.get("signature", "")),
                        categories=["symbol"],
                    ))

            command_index = cmap.get("command_index")
            if isinstance(command_index, dict):
                for command, locations in sorted(command_index.items()):
                    if not str(command).startswith("!"):
                        continue
                    if isinstance(locations, str):
                        locations = [locations]
                    if not isinstance(locations, list) or not locations:
                        continue
                    first_loc = str(locations[0])
                    file_part = first_loc.split(":", 1)[0]
                    skills.append(AuraSkill(
                        name=str(command),
                        kind="command",
                        path=file_part,
                        symbol=str(command),
                        description="Bang command " + str(command),
                        categories=["command"],
                    ))
                    json_commands_found = True
        except (json.JSONDecodeError, KeyError, OSError, TypeError):
            pass

    # 2. Legacy CODEMAP.md command index fallback only when JSON had none.
    codemap_md = os.path.join(repo_root, ".aura", "CODEMAP.md")
    if not json_commands_found and os.path.exists(codemap_md):
        try:
            with open(codemap_md, encoding="utf-8") as f:
                md_content = f.read()

            for m in re.finditer(r"- `(!\\w+)` -> (.+)", md_content):
                cmd = m.group(1)
                locations = m.group(2).strip()
                first_loc = locations.split(",")[0].strip()
                file_part = first_loc.split(":")[0].strip("`")
                skills.append(AuraSkill(
                    name=cmd,
                    kind="command",
                    path=file_part,
                    symbol=cmd,
                    description="Bang command " + cmd,
                    categories=["command"],
                ))
        except OSError:
            pass

'''


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    start = text.find(START)
    if start < 0:
        raise RuntimeError("SkillWeaver CODEMAP reader start marker missing")
    end = text.find(END, start)
    if end < 0:
        raise RuntimeError("SkillWeaver CODEMAP reader end marker missing")
    text = text[:start] + REPLACEMENT + text[end:]
    TARGET.write_text(text, encoding="utf-8")
    Path(__file__).unlink()
    print("SkillWeaver now consumes canonical CODEMAP symbol_index/command_index")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
