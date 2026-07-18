from __future__ import annotations

from pathlib import Path


def replace_between(path: str, start_marker: str, end_marker: str, replacement: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    start = text.find(start_marker)
    if start < 0:
        raise SystemExit(f"missing start marker in {path}: {start_marker!r}")
    end = text.find(end_marker, start)
    if end < 0:
        raise SystemExit(f"missing end marker in {path}: {end_marker!r}")
    target.write_text(text[:start] + replacement + text[end:], encoding="utf-8")


def main() -> None:
    # The first integration layer owns the three helper methods immediately
    # above this function. This refinement replaces only the resolver body so
    # the permanent class has one canonical helper definition for each owner.
    replace_between(
        "aura_review_arena.py",
        "    def _find_callsites(",
        "    def _run_tools(",
        '''    def _find_callsites(
        self,
        symbol: str,
        files: Sequence[str],
        *,
        target_file: str,
    ) -> list[dict[str, Any]]:
        target_modules = self._module_candidates_for_file(target_file)
        result: list[dict[str, Any]] = []
        for file in files:
            path = self._resolve_file(file)
            if path is None or not path.is_file():
                continue
            try:
                tree = ast.parse(
                    path.read_text(encoding="utf-8", errors="replace"),
                    filename=file,
                )
            except (OSError, SyntaxError):
                continue

            direct_aliases: dict[str, tuple[str, str]] = {}
            module_aliases: dict[str, str] = {}
            imported_modules: set[str] = set()
            for import_node in ast.walk(tree):
                if isinstance(import_node, ast.Import):
                    for alias in import_node.names:
                        imported_modules.add(alias.name)
                        local = alias.asname or alias.name.split(".", 1)[0]
                        module_aliases[local] = (
                            alias.name if alias.asname else alias.name.split(".", 1)[0]
                        )
                elif isinstance(import_node, ast.ImportFrom):
                    resolved_module = self._resolve_import_module(
                        file,
                        import_node.module,
                        import_node.level,
                    )
                    if resolved_module:
                        imported_modules.add(resolved_module)
                    for alias in import_node.names:
                        if alias.name == "*":
                            continue
                        local = alias.asname or alias.name
                        direct_aliases[local] = (resolved_module, alias.name)
                        imported_child = ".".join(
                            item for item in (resolved_module, alias.name) if item
                        )
                        if imported_child:
                            module_aliases[local] = imported_child

            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                resolution = ""
                target_resolved = False
                target_module = ""
                call_name = ""
                matches_symbol = False

                if isinstance(node.func, ast.Name):
                    call_name = node.func.id
                    imported = direct_aliases.get(call_name)
                    if imported and imported[1] == symbol:
                        matches_symbol = True
                        if imported[0] in target_modules:
                            target_resolved = True
                            resolution = "from_import"
                            target_module = imported[0]
                        else:
                            resolution = "imported_from_other_module"
                    elif call_name == symbol:
                        matches_symbol = True
                        if file == target_file:
                            target_resolved = True
                            resolution = "same_file"
                            target_module = next(iter(sorted(target_modules)), "")
                        else:
                            resolution = "ambiguous_name"
                elif isinstance(node.func, ast.Attribute):
                    dotted = self._dotted_name(node.func)
                    if not dotted or node.func.attr != symbol:
                        continue
                    call_name = symbol
                    matches_symbol = True
                    prefix = dotted.rsplit(".", 1)[0]
                    parts = prefix.split(".")
                    root = parts[0]
                    resolved_prefix = prefix
                    if root in module_aliases:
                        resolved_prefix = ".".join(
                            [module_aliases[root], *parts[1:]]
                        )
                    if resolved_prefix in target_modules and (
                        resolved_prefix in imported_modules
                        or root in module_aliases
                    ):
                        target_resolved = True
                        resolution = "module_attribute"
                        target_module = resolved_prefix
                    else:
                        resolution = "ambiguous_attribute"
                else:
                    continue

                if not matches_symbol:
                    continue
                result.append({
                    "file": file,
                    "line": int(node.lineno),
                    "local_call_name": call_name,
                    "original_symbol": symbol,
                    "positional_args": len(node.args),
                    "keyword_args": sorted(
                        keyword.arg for keyword in node.keywords if keyword.arg
                    ),
                    "starred": any(
                        isinstance(arg, ast.Starred) for arg in node.args
                    ) or any(keyword.arg is None for keyword in node.keywords),
                    "target_file": target_file,
                    "target_modules": sorted(target_modules),
                    "target_module": target_module,
                    "target_resolved": target_resolved,
                    "resolution": resolution,
                })
        return result

''',
    )


if __name__ == "__main__":
    main()
