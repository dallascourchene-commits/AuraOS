from __future__ import annotations

from pathlib import Path


def rewrite_required(path: str, transforms: list[tuple[str, str]]) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    for old, new in transforms:
        if old not in text:
            raise SystemExit(
                f"missing Coding Waboose integration fragment in {path}: {old[:120]!r}"
            )
        text = text.replace(old, new)
    target.write_text(text, encoding="utf-8")


def rewrite_optional(path: str, transforms: list[tuple[str, str]]) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    for old, new in transforms:
        text = text.replace(old, new)
    target.write_text(text, encoding="utf-8")


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


def patch_callsite_resolution() -> None:
    replace_between(
        "aura_review_arena.py",
        "    def _scan_signature_impacts(",
        "    @staticmethod\n    def _function_signatures",
        '''    def _scan_signature_impacts(self, state: Mapping[str, Any]) -> list[dict[str, Any]]:
        request: AuraReviewRequest = state["request"]
        if request.mode != "range":
            return []
        contract: AuraReviewContract = state["contract"]
        impact_files = sorted({
            str(item.get("file") or "") for item in contract.impact_slice
            if str(item.get("file") or "").endswith(".py")
        })[:80]
        findings: list[dict[str, Any]] = []
        for changed in contract.changed_files:
            if not changed.endswith(".py"):
                continue
            current_path = self._resolve_file(changed)
            if current_path is None or not current_path.exists():
                continue
            try:
                current = current_path.read_text(encoding="utf-8", errors="replace")
                base = self._git(
                    ["git", "show", f"{request.base_ref}:{changed}"], timeout=10
                )
            except (OSError, ValueError, subprocess.SubprocessError):
                continue
            old_signatures = self._function_signatures(base)
            new_signatures = self._function_signatures(current)
            changed_names = {
                name for name in set(old_signatures) | set(new_signatures)
                if old_signatures.get(name) != new_signatures.get(name)
            }
            for name in sorted(changed_names):
                old = old_signatures.get(name)
                new = new_signatures.get(name)
                callsites = self._find_callsites(
                    name,
                    impact_files,
                    target_file=changed,
                )
                if old and not new:
                    for callsite in callsites:
                        resolved = bool(callsite.get("target_resolved"))
                        findings.append({
                            "origin": "signature_impact",
                            "rule": "removed-symbol-callsite",
                            "category": "compatibility",
                            "severity": "high",
                            "confidence": 0.97 if resolved else 0.68,
                            "title": (
                                f"Resolved call site still references removed symbol {name}"
                                if resolved
                                else f"Same-named call may reference removed symbol {name}"
                            ),
                            "message": (
                                f"The import-resolved call targets {changed}, where {name} "
                                "is absent at the reviewed head."
                                if resolved
                                else f"A graph-related file calls {name}, but import resolution "
                                f"could not prove that it targets {changed}."
                            ),
                            "file": callsite["file"],
                            "line_start": callsite["line"],
                            "line_end": callsite["line"],
                            "related_files": [changed],
                            "related_symbols": [name],
                            "suggested_fix": (
                                "Update or remove the resolved call site, or restore a "
                                "compatibility facade."
                                if resolved
                                else "Resolve the call target before changing code."
                            ),
                            "evidence": [
                                {
                                    "kind": "signature_diff",
                                    "source": changed,
                                    "old": old,
                                    "new": None,
                                },
                                {"kind": "callsite", **callsite},
                            ],
                            "status": "corroborated" if resolved else "probable",
                        })
                elif (
                    old
                    and new
                    and int(new["required_positional"])
                    > int(old["required_positional"])
                ):
                    for callsite in callsites:
                        if callsite["starred"]:
                            continue
                        if int(callsite["positional_args"]) >= int(
                            new["required_positional"]
                        ):
                            continue
                        resolved = bool(callsite.get("target_resolved"))
                        findings.append({
                            "origin": "signature_impact",
                            "rule": "callsite-arity-mismatch",
                            "category": "compatibility",
                            "severity": "high",
                            "confidence": 0.97 if resolved else 0.72,
                            "title": (
                                f"Resolved call site does not satisfy the new {name} signature"
                                if resolved
                                else f"Same-named call may not satisfy the new {name} signature"
                            ),
                            "message": (
                                "The import-resolved call targets the reviewed function and "
                                "supplies fewer positional arguments than its new signature "
                                "requires."
                                if resolved
                                else "The call has too few arguments for the reviewed signature, "
                                "but the target remains ambiguous."
                            ),
                            "file": callsite["file"],
                            "line_start": callsite["line"],
                            "line_end": callsite["line"],
                            "related_files": [changed],
                            "related_symbols": [name],
                            "suggested_fix": (
                                "Update the resolved call site or provide a backwards-compatible "
                                "default."
                                if resolved
                                else "Resolve the call target before proposing a repair."
                            ),
                            "evidence": [
                                {
                                    "kind": "signature_diff",
                                    "source": changed,
                                    "old": old,
                                    "new": new,
                                },
                                {"kind": "callsite", **callsite},
                            ],
                            "status": "corroborated" if resolved else "probable",
                        })
        return findings

''',
    )
    replace_between(
        "aura_review_arena.py",
        "    def _find_callsites(",
        "    def _run_tools(",
        '''    @staticmethod
    def _module_candidates_for_file(file: str) -> set[str]:
        path = PurePosixPath(file)
        parts = list(path.with_suffix("").parts)
        if parts and parts[-1] == "__init__":
            parts.pop()
        candidates: set[str] = set()
        if parts:
            candidates.add(".".join(parts))
            if parts[0] in {"src", "lib"} and len(parts) > 1:
                candidates.add(".".join(parts[1:]))
        return {item for item in candidates if item}

    @staticmethod
    def _resolve_import_module(
        caller_file: str,
        module: str | None,
        level: int,
    ) -> str:
        module_parts = [part for part in str(module or "").split(".") if part]
        if level <= 0:
            return ".".join(module_parts)
        package_parts = list(PurePosixPath(caller_file).parent.parts)
        trim = max(0, level - 1)
        if trim:
            package_parts = package_parts[: max(0, len(package_parts) - trim)]
        return ".".join([*package_parts, *module_parts])

    @staticmethod
    def _dotted_name(node: ast.AST) -> str:
        parts: list[str] = []
        current: ast.AST | None = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
            return ".".join(reversed(parts))
        return ""

    def _find_callsites(
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

                if isinstance(node.func, ast.Name):
                    call_name = node.func.id
                    imported = direct_aliases.get(call_name)
                    if imported and imported[1] == symbol and imported[0] in target_modules:
                        target_resolved = True
                        resolution = "from_import"
                        target_module = imported[0]
                    elif file == target_file and call_name == symbol:
                        target_resolved = True
                        resolution = "same_file"
                        target_module = next(iter(sorted(target_modules)), "")
                    elif call_name == symbol:
                        resolution = "ambiguous_name"
                elif isinstance(node.func, ast.Attribute):
                    dotted = self._dotted_name(node.func)
                    if not dotted or node.func.attr != symbol:
                        continue
                    call_name = symbol
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

                if call_name != symbol:
                    continue
                result.append({
                    "file": file,
                    "line": int(node.lineno),
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


def patch_persistence_bridge() -> None:
    rewrite_required(
        "aura_agent_arena_persistence_bridge.py",
        [
            (
                "from aura_review_arena import AuraReviewArena",
                "from aura_coding_waboose import CodingWaboose",
            ),
            (
                "self.review_arena = AuraReviewArena(self.repo_root)",
                "self.coding_waboose = CodingWaboose(self.repo_root)",
            ),
            ("aura_review_prepare", "aura_waboose_prepare"),
            ("aura_review_scan", "aura_waboose_scan"),
            ("aura_review_agent_packet", "aura_waboose_agent_packet"),
            ("aura_review_submit_findings", "aura_waboose_submit_findings"),
            ("aura_review_finalize", "aura_waboose_finalize"),
            ("aura_review_status", "aura_waboose_status"),
            ("self.review_arena.", "self.coding_waboose."),
        ],
    )
    rewrite_optional(
        "aura_agent_arena_persistence_bridge.py",
        [
            ("graph-guided code-review contract", "Coding Waboose diagnostic contract"),
            ("prepared review", "prepared Coding Waboose run"),
            ("coding agent", "coding agent through Coding Waboose"),
        ],
    )


def patch_mcp() -> None:
    rewrite_required(
        "aura_agent_arena_mcp.py",
        [
            ("aura_review_prepare", "aura_waboose_prepare"),
            ("aura_review_scan", "aura_waboose_scan"),
            ("aura_review_agent_packet", "aura_waboose_agent_packet"),
            ("aura_review_submit_findings", "aura_waboose_submit_findings"),
            ("aura_review_finalize", "aura_waboose_finalize"),
            ("aura_review_status", "aura_waboose_status"),
            ("_handle_review_prepare", "_handle_waboose_prepare"),
            ("_handle_review_scan", "_handle_waboose_scan"),
            ("_handle_review_agent_packet", "_handle_waboose_agent_packet"),
            ("_handle_review_submit_findings", "_handle_waboose_submit_findings"),
            ("_handle_review_finalize", "_handle_waboose_finalize"),
            ("_handle_review_status", "_handle_waboose_status"),
        ],
    )
    rewrite_optional(
        "aura_agent_arena_mcp.py",
        [
            (
                "Compile an evidence-bound review contract from a Git range, workspace, or explicit files.",
                "Compile a Coding Waboose evidence contract and diagnostic breadboard from a Git range, workspace, or explicit files.",
            ),
            (
                "Run local deterministic scans and dependency-impact checks for a prepared review.",
                "Run Coding Waboose deterministic scans and energize the applicable diagnostic breadboard components.",
            ),
            (
                "Return the bounded focus, topology, evidence, and optional exact-source packet for a coding agent.",
                "Return Coding Waboose focus, diagnostic breadboard, topology, evidence, and optional exact-source slices for a coding agent.",
            ),
            (
                "Submit structured coding-agent findings for exact-source corroboration; agent confirmation claims are ignored.",
                "Submit Coding Waboose findings for exact-source corroboration; agent confirmation claims are ignored.",
            ),
            (
                "Deduplicate and rank findings, then compile review-only Forge repair requests.",
                "Deduplicate and rank Coding Waboose findings, then compile review-only Forge repair requests.",
            ),
            (
                "Return the bounded status and finding counts for an in-process review.",
                "Return Coding Waboose status, breadboard continuity, and finding counts.",
            ),
        ],
    )


def patch_mcp_tests() -> None:
    rewrite_required(
        "tests/test_aura_review_arena_mcp.py",
        [
            ("FakeReviewBridge", "FakeWabooseBridge"),
            ("aura_review_prepare", "aura_waboose_prepare"),
            ("aura_review_scan", "aura_waboose_scan"),
            ("aura_review_agent_packet", "aura_waboose_agent_packet"),
            ("aura_review_submit_findings", "aura_waboose_submit_findings"),
            ("aura_review_finalize", "aura_waboose_finalize"),
            ("aura_review_status", "aura_waboose_status"),
            ("review_tools_are_advertised", "waboose_tools_are_advertised"),
            ("review_prepare_dispatches_complete_request", "waboose_prepare_dispatches_complete_request"),
            ("review_lifecycle_tools_dispatch", "waboose_lifecycle_tools_dispatch"),
            (
                "plain_ok_false_review_result_sets_mcp_is_error",
                "plain_ok_false_waboose_result_sets_mcp_is_error",
            ),
        ],
    )


def patch_docs() -> None:
    for path in ("README.md", "USER_GUIDE.md", ".aura/ARCHITECTURE.md"):
        rewrite_optional(
            path,
            [
                ("Aura Review Arena", "Coding Waboose"),
                ("AURA_REVIEW_ARENA_V1", "AURA_CODING_WABOOSE_V1"),
                ("docs/AURA_REVIEW_ARENA.md", "docs/AURA_CODING_WABOOSE.md"),
                ("aura_review_arena_cli.py", "aura_coding_waboose_cli.py"),
                ("aura_review_contract.schema.json", "aura_coding_waboose_contract.schema.json"),
                ("aura_review_prepare", "aura_waboose_prepare"),
                ("aura_review_scan", "aura_waboose_scan"),
                ("aura_review_agent_packet", "aura_waboose_agent_packet"),
                ("aura_review_submit_findings", "aura_waboose_submit_findings"),
                ("aura_review_finalize", "aura_waboose_finalize"),
                ("aura_review_status", "aura_waboose_status"),
                ("Review Arena", "Coding Waboose"),
                (
                    "  → run-specific focus directives\n  → bounded coding-agent investigation",
                    "  → run-specific focus directives\n  → diagnostic Coding Breadboard\n  → bounded coding-agent investigation",
                ),
                (
                    "Use Coding Waboose when the question is not only \"does it compile?\" but also",
                    "Use Coding Waboose when the question is not only \"does it compile?\" but also\n\"which typed diagnostic circuit should be energized, and what exact forward and backward\nproof path does it require?\" Coding Waboose uses the Planning Board/Coding Breadboard when",
                ),
                (
                    "- `aura_review_arena.py`;\n- `aura_coding_waboose_cli.py`;\n- `schemas/aura_coding_waboose_contract.schema.json`;\n- Coding Waboose tools on `aura_agent_arena_persistence_bridge.py` and `aura_agent_arena_mcp.py`;\n- `docs/AURA_CODING_WABOOSE.md`.",
                    "- `aura_coding_waboose.py` — public Coding Waboose owner;\n- `aura_coding_waboose_breadboard.py` — proposal-only diagnostic circuit compiler;\n- `aura_review_arena.py` — internal reusable scan/corroboration engine;\n- `aura_coding_waboose_cli.py`;\n- `schemas/aura_coding_waboose_contract.schema.json` and the internal `schemas/aura_review_contract.schema.json`;\n- Coding Waboose tools on `aura_agent_arena_persistence_bridge.py` and `aura_agent_arena_mcp.py`;\n- `docs/AURA_CODING_WABOOSE.md`.",
                ),
            ],
        )


def patch_cli() -> None:
    rewrite_required(
        "aura_review_arena_cli.py",
        [
            (
                '\"\"\"Command-line interface for Aura Review Arena V1.\"\"\"',
                '\"\"\"Command-line interface for Coding Waboose V1.\"\"\"',
            ),
            (
                "from aura_review_arena import AuraReviewArena",
                "from aura_coding_waboose import CodingWaboose",
            ),
            (
                "Run Aura's graph-guided, evidence-bound code review Arena.",
                "Run Coding Waboose, Aura's graph-guided diagnostic code-review organ.",
            ),
            ("arena = AuraReviewArena(args.repo_root)", "arena = CodingWaboose(args.repo_root)"),
            ('\"version\": \"AURA_REVIEW_ARENA_V1\"', '\"version\": \"AURA_CODING_WABOOSE_V1\"'),
        ],
    )
    source = Path("aura_review_arena_cli.py")
    target = Path("aura_coding_waboose_cli.py")
    target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    source.unlink()


def main() -> None:
    patch_callsite_resolution()
    patch_persistence_bridge()
    patch_mcp()
    patch_mcp_tests()
    patch_docs()
    patch_cli()


if __name__ == "__main__":
    main()
