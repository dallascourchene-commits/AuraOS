from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "aura_skillweaver.py"

OLD = '''def build_skill_registry(repo_root=None):
    """Build a lightweight skill registry from CODEMAP and MASTER_KEY headers."""
    if repo_root is None:
        repo_root = os.path.dirname(os.path.abspath(__file__))

    skills = []

    # 1. Parse CODEMAP.json for module/function entries
    codemap_json = os.path.join(repo_root, ".aura", "CODEMAP.json")
    if os.path.exists(codemap_json):
        try:
            with open(codemap_json, encoding="utf-8") as f:
                cmap = json.load(f)

            for entry in cmap.get("files", []):
                path = entry.get("path", "")
                role = entry.get("role", "")
                if role == "python_module" and path.endswith(".py"):
                    name = os.path.splitext(os.path.basename(path))[0]
                    deps_str = entry.get("dependencies", "")
                    deps = deps_str.split(", ") if deps_str else []
                    skills.append(AuraSkill(
                        name=name,
                        kind="module",
                        path=path,
                        symbol=None,
                        description=entry.get("synopsis", "")[:200],
                        categories=[role],
                        dependencies=deps,
                    ))

            for sym in cmap.get("symbols", []):
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

    # 2. Parse CODEMAP.md command index for bang commands
    codemap_md = os.path.join(repo_root, ".aura", "CODEMAP.md")
    if os.path.exists(codemap_md):
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
        except Exception:
            pass
'''

NEW = '''def build_skill_registry(repo_root=None):
    """Build a lightweight skill registry from the canonical CODEMAP surface."""
    if repo_root is None:
        repo_root = os.path.dirname(os.path.abspath(__file__))

    skills = []
    command_names = set()

    # 1. Parse canonical CODEMAP.json for module/function/command entries.
    codemap_json = os.path.join(repo_root, ".aura", "CODEMAP.json")
    if os.path.exists(codemap_json):
        try:
            with open(codemap_json, encoding="utf-8") as f:
                cmap = json.load(f)

            for entry in cmap.get("files", []):
                path = entry.get("path", "")
                role = entry.get("role", "")
                if role == "python_module" and path.endswith(".py"):
                    name = os.path.splitext(os.path.basename(path))[0]
                    deps_str = entry.get("dependencies", "")
                    deps = deps_str.split(", ") if deps_str else []
                    skills.append(AuraSkill(
                        name=name,
                        kind="module",
                        path=path,
                        symbol=None,
                        description=entry.get("synopsis", "")[:200],
                        categories=[role],
                        dependencies=deps,
                    ))

            symbol_index = cmap.get("symbol_index", {})
            if isinstance(symbol_index, dict):
                for name, entries in symbol_index.items():
                    if not isinstance(entries, list):
                        continue
                    for sym in entries:
                        if not isinstance(sym, dict):
                            continue
                        skills.append(AuraSkill(
                            name=str(name),
                            kind="function",
                            path=sym.get("file", ""),
                            symbol=str(name),
                            description=str(sym.get("signature", "")),
                            categories=["symbol"],
                        ))

            command_index = cmap.get("command_index", {})
            if isinstance(command_index, dict):
                for cmd, locations in sorted(command_index.items()):
                    if not isinstance(cmd, str) or not cmd.startswith("!"):
                        continue
                    if not isinstance(locations, list) or not locations:
                        continue
                    first_loc = str(locations[0])
                    file_part = first_loc.rsplit(":", 1)[0] if ":" in first_loc else first_loc
                    skills.append(AuraSkill(
                        name=cmd,
                        kind="command",
                        path=file_part,
                        symbol=cmd,
                        description="Bang command " + cmd,
                        categories=["command"],
                    ))
                    command_names.add(cmd)
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

    # 2. Legacy fallback only: old CODEMAP.md builds rendered a command index.
    codemap_md = os.path.join(repo_root, ".aura", "CODEMAP.md")
    if os.path.exists(codemap_md):
        try:
            with open(codemap_md, encoding="utf-8") as f:
                md_content = f.read()

            for m in re.finditer(r"- `(!\\w+)` -> (.+)", md_content):
                cmd = m.group(1)
                if cmd in command_names:
                    continue
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
                command_names.add(cmd)
        except Exception:
            pass
'''


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    count = text.count(OLD)
    if count != 1:
        raise RuntimeError(f"SkillWeaver CODEMAP registry anchor expected once, found {count}")
    TARGET.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    Path(__file__).unlink()
    print("SkillWeaver registry now binds commands to canonical CODEMAP.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
